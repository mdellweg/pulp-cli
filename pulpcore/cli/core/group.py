import click

from pulpcore.cli.common.generic import (
    list_entities,
    show_by_name,
    destroy_by_name,
)
from pulpcore.cli.common.context import (
    pass_pulp_context,
    pass_entity_context,
    PulpContext,
    PulpEntityContext,
)
from pulpcore.cli.core.context import (
    PulpGroupContext,
    PulpGroupPermissionContext,
    PulpGroupModelPermissionContext,
    PulpGroupObjectPermissionContext,
    PulpGroupUserContext,
    PulpUserContext,
)


@click.group()
@pass_pulp_context
@click.pass_context
def group(ctx: click.Context, pulp_ctx: PulpContext) -> None:
    ctx.obj = PulpGroupContext(pulp_ctx)


group.add_command(list_entities)
group.add_command(show_by_name)


@group.command()
@click.option("--name", required=True)
@pass_entity_context
@pass_pulp_context
def create(pulp_ctx: PulpContext, entity_ctx: PulpEntityContext, name: str) -> None:
    entity = {"name": name}
    result = entity_ctx.create(body=entity)
    pulp_ctx.output_result(result)


group.add_command(destroy_by_name)


@group.group()
@click.option(
    "-t",
    "--type",
    "perm_type",
    type=click.Choice(["model", "object"], case_sensitive=False),
    default="model",
)
@click.option("--groupname", required=True)
@pass_entity_context
@pass_pulp_context
@click.pass_context
def permission(
    ctx: click.Context,
    pulp_ctx: PulpContext,
    group_ctx: PulpGroupContext,
    perm_type: str,
    groupname: str,
) -> None:
    if perm_type == "model":
        ctx.obj = PulpGroupModelPermissionContext(pulp_ctx)
    elif perm_type == "object":
        ctx.obj = PulpGroupObjectPermissionContext(pulp_ctx)
    else:
        raise NotImplementedError()
    ctx.obj.group = group_ctx.find(name=groupname)


permission.add_command(list_entities)


@permission.command(name="add")
@click.option("--permission", required=True)
@pass_entity_context
def add_permission(entity_ctx: PulpGroupPermissionContext, permission: str) -> None:
    body = {"permission": permission}
    entity_ctx.create(body=body)


@permission.command(name="remove")
@click.option("--permission", required=True)
@pass_entity_context
@pass_pulp_context
def remove_permission(
    pulp_ctx: PulpContext, entity_ctx: PulpGroupPermissionContext, permission: str
) -> None:
    perm_href = entity_ctx.find(permission=permission)["pulp_href"]
    entity_ctx.delete(perm_href)


@group.group()
@click.option("--groupname", required=True)
@pass_entity_context
@pass_pulp_context
@click.pass_context
def user(
    ctx: click.Context, pulp_ctx: PulpContext, group_ctx: PulpGroupContext, groupname: str
) -> None:
    ctx.obj = PulpGroupUserContext(pulp_ctx)
    ctx.obj.group = group_ctx.find(name=groupname)


user.add_command(list_entities)


@user.command(name="add")
@click.option("--username", required=True)
@pass_entity_context
def add_user(entity_ctx: PulpGroupUserContext, username: str) -> None:
    entity_ctx.create(body={"username": username})


@user.command(name="remove")
@click.option("--username", required=True)
@pass_entity_context
@pass_pulp_context
def remove_user(pulp_ctx: PulpContext, entity_ctx: PulpGroupUserContext, username: str) -> None:
    user_href = PulpUserContext(pulp_ctx).find(username=username)["pulp_href"]
    user_pk = user_href.split("/")[-2]
    group_user_href = entity_ctx.group["pulp_href"] + "users/" + user_pk
    entity_ctx.delete(group_user_href)
