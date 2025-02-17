import click

from ocrd.decorators import ocrd_cli_options, ocrd_cli_wrap_processor
from .processor import PAGE2PDF

@click.command()
@ocrd_cli_options
def ocrd_pagetopdf(*args, **kwargs):
    return ocrd_cli_wrap_processor(PAGE2PDF, *args, **kwargs)
