from pulp_cli.generic import PulpCLIContext, pass_pulp_context, pulp_command


@pulp_command()
@pass_pulp_context
def login(pulp_ctx: PulpCLIContext, /) -> None:
    pulp_ctx.call("login")


@pulp_command()
@pass_pulp_context
def logout(pulp_ctx: PulpCLIContext, /) -> None:
    pulp_ctx.call("logout")
