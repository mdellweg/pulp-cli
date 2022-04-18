# Pulpkit (working title) Architecture

* openapi.py
  + `OpenApi`
    - takes care of downloading and caching the schema
    - reads and parses the schema
    - performes requests calls according to schema by operation id
    - not pulp specific
    - openapi3 compatible
    - raises OpenApiError

* context.py (maybe rename to pulpkit.py)
  + `PulpContext`
    - Pulp specific
    - keeps a lazy instance of OpenApi loaded with connection details for a pulp server
    - Provides a higher level call interface that transparently handles tasks and translates OpenApiError to PulpException
    - `has_plugin` and `needs_plugin`
  + `PulpEntityContext` and sub classes (maybe rename to PulpEntity; maybe separate Entity from EntityContext)
    - keeps a reference to the global `PulpContext`
    - keeps a copy of an entity (`dict`) or lookup (`dict`) attributes
    - transparently performes lookup
    - provides a call interface that maps operation ("read", "destroy", ...) to operation id
    - provides richer `read`, `destroy`, ... functions in orm fashion
  + `Pulp<...>Context(PulpEntityContext)`
    - specific to certain Pulp entities
    - represents the interface to a specific entity in Pulp
    - provides `PREFIX_ID` and non-standard `<OPERATION>_ID`s
    - implements special REST calls (like `repair`)
    - defines `CAPABILITIES`
    - implements version dependent workarounds for API quirks
    - will be shipped with the cli plugins
  + context registries for generic operations like import export
  + `PluginRequirement`

* common.py (Pulp-click glue layer)
  + `PulpClickContext(PulpContext)`
    - translate `PulpException` into `ClickException`
    - `output_result`
  + `PulpCommand`, `pulp_command`
  + `PulpGroup`, `pulp_group`
  + `PulpParameter`, `pulp_parameter`
  + helpers for command groups

* [squeezer] `plugins/module_utils/pulp.py`
  + `PulpAnsibleModule(AnsibleModule)`
    - Pulp specific
    - keeps an instance of PulpContext loaded with connection details for a pulp server
    - translates `PulpException` to `fail_json` (context manager)
  + `PulpEntityAnsibleModule(PulpAnsibleModule)`
    - provides `state` parameter and handles idempotence
    - translates `pulp_spec` to `parameter_spec`

* [squeezer] `plugins/modules/pulp_<...>.py`
  + `Pulp<...>Module(PulpAnsibleModule)`
    - keeps an instance of `Pulp<...>Context`
    - defines ansible module parameter (`pulp_spec`)
    - module documentation and examples
