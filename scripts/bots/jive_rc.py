"""Upstream JiveRC name; NatureCrafter remains available for saved configurations."""

from bots.nature_crafter import NatureCrafter, SETTINGS

BOT = define_bot(name='JiveRC', create=NatureCrafter, category='Runecrafting', tags=['runecrafting', 'trade', 'cosmic'],
                 settings_schema=SETTINGS, description='Master and runner crafting for Nature, Air and Cosmic runes. Cosmic starts in Zanaris or the Cosmic altar.')
