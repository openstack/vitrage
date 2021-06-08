============================
So You Want to Contribute...
============================

For general information on contributing to OpenStack, please check out the
`contributor guide <https://docs.openstack.org/contributors/>`_ to get started.
It covers all the basics that are common to all OpenStack projects: the accounts
you need, the basics of interacting with our Gerrit review system, how we
communicate as a community, etc.

Below will cover the more project specific information you need to get started
with Vitrage.

Communication
~~~~~~~~~~~~~

* IRC channel #openstack-vitrage at OFTC
* Mailing list (prefix subjects with ``[vitrage]`` for faster responses)
  http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack-discuss

Contacting the Core Team
~~~~~~~~~~~~~~~~~~~~~~~~

* Core Contributors/Reviewers
  https://review.opendev.org/#/admin/groups/1110,members


New Feature Planning
~~~~~~~~~~~~~~~~~~~~

If you want to add new functionality to Vitrage please file a blueprint
by following https://blueprints.launchpad.net/vitrage/+addspec

We don't have a strict requirement to write a detailed specification for
all new features and rather encourage more agile approach: just file a
brief description of a feature in the form of blueprint and then send a
patch to review (linking it to the blueprint). However, in some rare cases,
like proposing new API, we need a spec so that the team could fully understand
what's going to be done and provide a feedback.

To file a specification for a new feature, send a patch to
https://opendev.org/openstack/vitrage-specs that adds a new spec file
for the needed release cycle (e.g. 'specs/victoria')

The full list of the specs can be seen at
https://specs.openstack.org/openstack/vitrage-specs/

Task Tracking
~~~~~~~~~~~~~
We track our tasks in
`Storyboard
<https://storyboard.openstack.org/#!/project/openstack/vitrage>`_.

If you're looking for some smaller, easier work item to pick up and get started
on, search for the 'low-hanging-fruit' tag.

Reporting a Bug
~~~~~~~~~~~~~~~
If you have found an issue and want to make sure we are aware of it, please
report the issue on
`Storyboard
<https://storyboard.openstack.org/#!/project/openstack/vitrage>`_.

Where to Make Code Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~

Vitrage has a number of repositories where you can make code changes:

* https://github.com/openstack/vitrage
* https://github.com/openstack/python-vitrageclient
* https://github.com/openstack/vitrage-dashboard


Where to Review Code Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* https://review.opendev.org/#/q/vitrage
* https://review.opendev.org/#/q/python-vitrageclient
* https://review.opendev.org/#/q/vitrage-dashboard


Getting Your Patch Merged
~~~~~~~~~~~~~~~~~~~~~~~~~

Typically a patch can be merged when it has two +2 votes (at least two core
members voted +2). In some rare emergency cases we allow one +2 vote before
approving it.

A patch cannot be merged if it has at least one negative vote!

Project Team Lead Duties
~~~~~~~~~~~~~~~~~~~~~~~~

All common PTL duties are enumerated in the `PTL guide
<https://docs.openstack.org/project-team-guide/ptl.html>`_.

