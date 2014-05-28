Transitions
===========

Give the opportunity to take advantage of the transition, which facilitating multi-changes in assets including generation report file.

Configuration
~~~~~~~~~~~~~

Transition is disabled by default. To enable it, set settings as follow::

    ASSETS_TRANSITIONS['ENABLE'] = True

Defining your own transition requires adding transition object to the database. Actually we support following transitions: ``RELEASE-ASSET``, ``LOAN-ASSET``, ``RETURN-ASSET``.

Each transition has default slug defined in settings. You don't have to change anything in settings and use predefined slugs in transition definition objects.

To change slugs update settings variable eg.::

    ASSETS_TRANSITIONS['SLUGS']['RELEASE'] = "your-custom-slug"

Default slugs:

    * ``release-asset`` - for ``RELEASE-ASSET`` transition
    * ``loan-asset`` - for ``LOAN-ASSET`` transition
    * ``return-asset`` - for ``RETURN-ASSET`` transition

Actions available in transitions:

    * ``assign_loan_end_date`` - fill loan end date in form.
    * ``assign_owner`` - assign new user into assets.
    * ``assign_user`` - assign new owner into assets.
    * ``assign_warehouse`` -  assign new warehouse into assets.
    * ``change_status`` - change status into defined in ``to_status`` Transition field.
    * ``release_report`` - generate release report file.
    * ``return_report`` - generate return report file.
    * ``unassign_licences`` - remove all licences assigned into assets.
    * ``unassign_loan_end_date`` - clear loan end date field in assets.
    * ``unassign_owner`` - remove owner assigned into assets.
    * ``unassign_user`` - remove user assigned into assets.


Reports
-------

To generate reports files, report template should be uploaded into 'Report odt source' model. Created model's slug should be specified. lub Created model should have specified slug.
And configure `INKPY <https://pypi.python.org/pypi/inkpy>`_  module.

Slug definition per report may be overridden in settings file eg.::

    ASSETS_REPORTS['RELEASE-ASSET']['SLUG'] = 'your-slug'

You can use predefined slugs:

    * ``release-asset`` - for release asset transition
    * ``loan-asset`` - for loan asset transition
    * ``return-asset`` - for return asset transition

