"""Swap this one import to change the rich text editor everywhere it's used."""

from django_ckeditor_5.fields import CKEditor5Field


def RichTextField(*args, config_name="default", **kwargs):
    return CKEditor5Field(*args, config_name=config_name, **kwargs)
