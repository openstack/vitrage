# Copyright 2018 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from oslo_log import log

from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_functions import GET_PARAM
from vitrage.evaluator.template_validation.base import ValidationError

LOG = log.getLogger(__name__)


def get_attr(match, *args):
    """Get the runtime value of an attribute of a template entity

    Usage: get_attr(template_id, attr_name)

    Example:

    scenario:
     condition: alarm_on_host_1
     actions:
       action:
         action_type: execute_mistral
         properties:
           workflow: demo_workflow
           input:
             host_name: get_attr(host_1,name)
             retries: 5

    get_attr(host_1, name) will return the name of the host that was matched
    by the evaluator to host_1

    :param match: The evaluator's match structure. A dictionary of
    {template_id, Vertex}
    :param args: The arguments of the function. For get_attr, the expected
    arguments are:
    - template_id: The internal template id of the entity
    - attr_name: The name of the wanted attribute
    :return: The wanted attribute if found, or None
    """

    if len(args) != 2:
        LOG.warning('Called function get_attr with wrong number of '
                    'arguments: %s. Usage: get_attr(vertex, attr_name)',
                    args)
        return

    template_id = args[0]
    attr_name = args[1]
    vertex = match.get(template_id)

    if not vertex:
        LOG.warning('Called function get_attr with unknown template_id %s',
                    args[0])
        return

    entity_props = vertex.properties
    attr = entity_props.get(attr_name) if entity_props else None

    if attr is None:
        LOG.warning('Attribute %s not found for vertex %s',
                    attr_name, vertex)

    LOG.debug('Function get_attr called with template_id %s and attr_name %s.'
              'Matched vertex properties: %s. Returned attribute value: %s',
              template_id, attr_name, entity_props, attr)

    return attr


def get_param(param_name, template, **kwargs):
    """Return the value of a specific parameter that is used in a template

    Usage: get_param(param_name, template, actual_params)

    Example:

    parameters:
     new_state:
      default: ERROR
    scenarios:
     - scenario:
        condition: alarm_on_host
        actions:
         - action:
            action_type: set_state
            properties:
             state: get_param(new_state)
            action_target:
             target: resource

    actual_params may be empty or may define a new_state parameter:
    {'new_state': 'SUBOPTIMAL'}

    :param param_name: Name of a parameter
    :param template: Complete template structure
    :param kwargs: Additional arguments.
    The expected argument is actual_params, a dict with key=value pairs of
    parameter values.
    :return: The parameter value is taken from the actual_params, if given, or
    from the default value that is defined in the template parameters section.
    If none exists, or param_name does not contains a valid function call
    a ValidationError is raised.
    :raises: ValidationError
    """
    param_defs = template.get(TemplateFields.PARAMETERS)
    actual_params = kwargs.get('actual_params')

    if not param_defs:
        raise ValidationError(161)

    if param_name.startswith(GET_PARAM):
        if not param_name.startswith(GET_PARAM + '(') or \
                not param_name.endswith(')') or \
                len(param_name) < len(GET_PARAM) + 3:
            raise ValidationError(162, param_name)

    extracted_param_name = extract_param_name(param_name)
    if not extracted_param_name:
        raise ValidationError(162, param_name)

    # Make sure the parameter is defined in the parameters section
    found_param_def = None
    for param_key, param_value in param_defs.items():
        if extracted_param_name == param_key:
            found_param_def = param_key, param_value

    if not found_param_def:
        raise ValidationError(161, extracted_param_name)

    # Check if an actual value was assigned to this parameter
    param_value = get_actual_value(extracted_param_name, actual_params)
    if not param_value:
        found_param_value = found_param_def[1]
        default = found_param_value.get(TemplateFields.DEFAULT) \
            if found_param_value else None  # param_def may have a None value
        if default:
            param_value = default
        else:
            raise ValidationError(163, extracted_param_name)

    return param_value


def extract_param_name(param):
    param_name = param[len(GET_PARAM):]
    if len(param_name) > 2 and \
            param_name[0] == '(' and param_name[-1] == ')':
        param_name = param_name[1:-1]
    return param_name


def get_actual_value(param_name, actual_params):
    if actual_params:
        return actual_params.get(param_name)
