#! /usr/bin/env python

import sys
import os
import json


def item2json(item):
    if item is None:
        return None

    return {
        'id': item.id,
        'name': item.name,
        'quality': item.get_quality_name(),
        'level': item.itemLevel,
        'upgrade': item.upgrade if item.upgradable else {},
        'icon': item.get_icon_url(size='small'),
        'random_enchant': item.random_enchant,
        'enchant': item.enchant,
        'reforge': item.reforge,
        'extra_socket': item.extra_socket,
        'gems': item.gems.values(),
        'set': item.set,
    }


AMR_SLOTS_ID = [
    'head',
    'neck',
    'shoulder',
    None,
    'chest',
    'waist',
    'legs',
    'feet',
    'wrist',
    'hands',
    'finger1',
    'finger2',
    'trinket1',
    'trinket2',
    'back',
    'main_hand',
    'off_hand',
]


ENCHANTS = {}
REFORGES = {}



# Modify the path to be able to import the 'battlenet' library
script_path = os.path.dirname(sys.argv[0])
if os.path.exists(os.path.join(script_path, 'battlenet/battlenet/__init__.py')):
    sys.path.insert(0, os.path.join(script_path, 'battlenet'))


# battlenet importations
import battlenet
from battlenet import Connection
from battlenet import Character


# Process the command-line arguments
if (len(sys.argv) > 4) or ((len(sys.argv) > 2) and (sys.argv[1] != '--data')):
    print "Usage: %s [--data <path>] [<output_folder>]" % sys.argv[0]
    print
    sys.exit(-1)


if len(sys.argv) == 4:
    wtf_path = sys.argv[2]
    dest = sys.argv[3]
elif len(sys.argv) == 3:
    wtf_path = sys.argv[2]
    dest = './html'
elif len(sys.argv) == 2:
    wtf_path = None
    dest = sys.argv[1]
else:
    wtf_path = None
    dest = './html'

dest = os.path.abspath(dest)


# Try to import the user's custom settings
try:
    settings = __import__('settings')

    if not(hasattr(settings, 'CHARACTER_NAMES')):
        print 'No CHARACTER_NAMES option found in the settings file'
        sys.exit(-1)

    if not(hasattr(settings, 'LOCALE')):
        print 'No LOCALE option found in the settings file'
        sys.exit(-1)
except:
    import traceback
    print 'Failed to load the settings file, reason:\n' + traceback.format_exc()
    sys.exit(-1)



# Import the list of enchantments (if needed)
if wtf_path is not None:
    file = open(os.path.join(script_path, 'data/enchants.txt'), 'r')
    lines = filter(lambda x: len(x) > 0, file.readlines())
    file.close()

    for line in lines:
        parts = line.strip().split(',')

        id = parts[0]
        effect = ','.join(parts[1:])

        if (id != '') and (effect != ''):
            ENCHANTS[id.replace('"', '')] = effect.replace('"', '')


# Import the list of reforges (if needed)
if wtf_path is not None:
    file = open(os.path.join(script_path, 'data/reforges.txt'), 'r')
    lines = filter(lambda x: len(x) > 0, file.readlines())
    file.close()

    for line in lines:
        (id, src, dst) = line.strip().split(',')
        if (id != '') and (src != '') and (dst != ''):
            REFORGES[id] = '%s -> %s' % (src, dst)


# Setup the connection
Connection.setup(locale=settings.LOCALE)


# Import the data file (if one exist)
json_data = None
if os.path.exists(os.path.join(dest, 'data.json')):
    file = open(os.path.join(dest, 'data.json'), 'r')
    json_data = json.load(file)
    file.close()

    # Ensure that the format is still valid (in case of update of the format)
    if len(json_data['characters']) > 0:
        json_character =  json_data['characters'][0]
        if not(json_character.has_key('specs')):
            json_data = None

if json_data is None:
    json_data = {
        'characters': [],
        'items': {},
        'locale': settings.LOCALE,
    }


# Complete the data
for (region, server, name, specs) in settings.CHARACTER_NAMES:
    try:
        print "Retrieving '%s (%s - %s)'..." % (name, server, region)
        character = Character(region, server, name,
                              fields=[Character.ITEMS, Character.TALENTS])
    except:
        print "    FAILED"
        continue


    # Known character or new one?
    json_character = filter(lambda x: x['name'] == name, json_data['characters'])
    if len(json_character) == 1:
        json_character = json_character[0]
        json_character['level'] = character.level
        json_character['max_ilvl'] = character.equipment.average_item_level

        known_specs = map(lambda x: x['name'], json_character['specs'])
        specs_to_add = filter(lambda x: x not in known_specs, specs)
        for spec in specs_to_add:
            json_spec = {
                'name': spec,
                'ilvl': None,
                'role': None,
                'icon': None,
                'items': {},
                'modifications': {},
                'valid_modifications': True,
            }

            json_character['specs'].append(json_spec)

        specs_to_remove = filter(lambda x: x['name'] not in specs, json_character['specs'])
        for spec in specs_to_remove:
            json_character['specs'].remove(spec)

    else:
        json_character = {
            'name': character.name,
            'level': character.level,
            'class': character.get_class_name(),
            'max_ilvl': character.equipment.average_item_level,
            'armory_url': 'http://%s.battle.net/wow/%s/character/%s/%s/advanced' % (region, settings.LOCALE, character.get_realm_name(), character.name),
            'specs': [],
        }

        for spec in specs:
            json_spec = {
                'name': spec,
                'ilvl': None,
                'role': None,
                'icon': None,
                'items': {},
                'modifications': {},
                'valid_modifications': True,
            }

            json_character['specs'].append(json_spec)


        json_data['characters'].append(json_character)


    # Process the active spec
    active_talents = filter(lambda x: x.selected, character.talents)[0]
    if active_talents.name not in specs:
        print "    Active spec must not be displayed: '%s'" % active_talents.name
        continue

    json_spec = filter(lambda x: x['name'] == active_talents.name, json_character['specs'])[0]

    json_spec['role'] = active_talents.role
    json_spec['ilvl'] = character.equipment.average_item_level_equipped
    json_spec['icon'] = active_talents.get_icon_url(size='small')

    json_spec['modifications']       = {}
    json_spec['valid_modifications'] = True

    json_spec['items']['main_hand'] = item2json(character.equipment.main_hand)
    json_spec['items']['off_hand']  = item2json(character.equipment.off_hand)
    json_spec['items']['head']      = item2json(character.equipment.head)
    json_spec['items']['neck']      = item2json(character.equipment.neck)
    json_spec['items']['shoulder']  = item2json(character.equipment.shoulder)
    json_spec['items']['back']      = item2json(character.equipment.back)
    json_spec['items']['chest']     = item2json(character.equipment.chest)
    json_spec['items']['wrist']     = item2json(character.equipment.wrist)
    json_spec['items']['hands']     = item2json(character.equipment.hands)
    json_spec['items']['waist']     = item2json(character.equipment.waist)
    json_spec['items']['legs']      = item2json(character.equipment.legs)
    json_spec['items']['feet']      = item2json(character.equipment.feet)
    json_spec['items']['finger1']   = item2json(character.equipment.finger1)
    json_spec['items']['finger2']   = item2json(character.equipment.finger2)
    json_spec['items']['trinket1']  = item2json(character.equipment.trinket1)
    json_spec['items']['trinket2']  = item2json(character.equipment.trinket2)


    # Process AskMrRobot's data
    if wtf_path is not None:
        path = os.path.join(wtf_path, server, name, 'SavedVariables', 'AskMrRobot.lua')
        if os.path.exists(path):
            file = open(path, 'r')
            lines = file.readlines()
            file.close()

            import_data = filter(lambda x: x.startswith('AmrImportString = '), lines)
            if len(import_data) == 1:
                parsed_items = filter(lambda x: x.startswith('item='), import_data[0].split(';'))
                for item in parsed_items:
                    parts = item.split(':')
                    slot = int(parts[0][5:])
                    item_id = int(parts[1])
                    gems = map(lambda x: int(x), parts[6].split(','))
                    enchant = int(parts[7])
                    reforge = int(parts[8])

                    if (len(gems) == 1) and (gems[0] == 0):
                        gems = []

                    if enchant == 0:
                        enchant = None

                    if reforge == 0:
                        reforge = None

                    item = getattr(character.equipment, AMR_SLOTS_ID[slot])
                    if item is not None:
                        if item_id != item.id:
                            json_spec['valid_modifications'] = False
                            break

                        modifs = {
                            'gems': [None] * len(gems),
                            'enchant': None,
                            'reforge': None,
                        }

                        for index, gem in enumerate(gems):
                            if (gem != item.gems[index]) and (gem != 0):
                                if not(json_data['items']).has_key(str(gem)):
                                    print "    Retrieving gem #%d..." % gem
                                    connection = Connection()
                                    json_gem = connection.get_item(region, gem)
                                    if json_gem is not None:
                                        json_data['items'][str(gem)] = json_gem
                                        print "        %s" % json_gem['name'].encode('utf-8')
                                    else:
                                        json_data['items'][str(gem)] = None
                                        print "        FAILED"

                                modifs['gems'][index] = gem

                        if enchant != item.enchant:
                            try:
                                modifs['enchant'] = ENCHANTS[str(enchant)]
                            except:
                                modifs['enchant'] = 'Unknown enchant (%s)' % str(enchant)

                        if (reforge != item.reforge) and (reforge != 0):
                            try:
                                if reforge is None:
                                    modifs['reforge'] = 'Remove reforge'
                                else:
                                    modifs['reforge'] = REFORGES[str(reforge)]
                            except:
                                modifs['reforge'] = 'Unknown reforge (%s)' % str(reforge)

                        json_spec['modifications'][AMR_SLOTS_ID[slot]] = modifs


# Generate the JSON file
output_file = open(os.path.join(dest, 'data.json'), 'w')
output_file.write(json.dumps(json_data, indent=4))
output_file.close()
