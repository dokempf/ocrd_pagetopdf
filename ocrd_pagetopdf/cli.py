import click

from ocrd.decorators import ocrd_cli_options, ocrd_cli_wrap_processor
from .page_processor import PAGE2PDF
from .alto_processor import ALTO2PDF

@click.command()
@ocrd_cli_options
def ocrd_pagetopdf(*args, **kwargs):
    return ocrd_cli_wrap_processor(PAGE2PDF, *args, **kwargs)

@click.command()
@ocrd_cli_options
def ocrd_altotopdf(*args, **kwargs):
    return ocrd_cli_wrap_processor(ALTO2PDF, *args, **kwargs)
