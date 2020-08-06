==================
vitrage-purge-data
==================

---------------------------------------------
CLI interface for Vitrage Purge Data commands
---------------------------------------------

Synopsis
========

::

  vitrage-purge-data --config-file [<args>]

Description
===========

:program:`vitrage-purge-data` is a tool that provides routines for clearing
the data of a Vitrage deployment tables.

Options
=======

The standard pattern for executing a :program:`vitrage-purge-data` command is::

    vitrage-purge-data --config-file /etc/vitrage/vitrage.conf


The section describe those tables that are emptied after executing the command

  **Related Tables**

  .. list-table::
     :widths: 20 80
     :header-rows: 1

     * - Number
       - Table Name
     * - 1
       - active_actions
     * - 2
       - events
     * - 3
       - graph_snapshots
     * - 4
       - changes
     * - 5
       - edges
     * - 6
       - alarms
