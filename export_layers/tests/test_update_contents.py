# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *

import pickle

import gimpenums

import unittest

import mock

from export_layers import pygimplib as pg

from export_layers.pygimplib.tests import stubs_gimp

from export_layers import actions as actions_
from export_layers import export as export_
from export_layers import settings_main
from export_layers import update


ORIG_SETTINGS = settings_main.create_settings()

SESSION_DATA_3_3_1 = b'ccollections\nOrderedDict\np1\n((lp2\n(lp3\nVmain/available_tags\np4\na(dp5\nVforeground\np6\nVForeground\np7\nsVbackground\np8\nVBackground\np9\nsaa(lp10\nVmain/file_extension\np11\naVjpg\np12\naa(lp13\nVmain/output_directory\np14\naVC:\\u005cUsers\\u005cMyUsername\np15\naa(lp16\nVmain/layer_filename_pattern\np17\naV[layer name, %e]_[layer path, _]\np18\naa(lp19\nVmain/overwrite_mode\np20\naI2\naa(lp21\nVmain/plugin_version\np22\naV3.3.1\np23\naa(lp24\nVmain/procedures/_added_data\np25\na(lp26\nccopy_reg\n_reconstructor\np27\n(cfuture.types.newdict\nnewdict\np28\nc__builtin__\ndict\np29\n(dp30\nVfunction\np31\ncexport_layers.builtin_procedures\ninsert_background_layer\np32\nsVorig_name\np33\nVinsert_background_layers\np34\nsVdisplay_name\np35\nVInsert background layers\np36\nsVname\np37\ng34\nsVarguments\np38\n(lp39\n(dp40\nVdefault_value\np41\nVbackground\np42\nsVtype\np43\ncexport_layers.pygimplib.pgsetting\nStringSetting\np44\nsg37\nVtag\np45\nsastRp46\nag27\n(g28\ng29\n(dp47\ng31\ncexport_layers.builtin_procedures\nresize_to_layer_size\np48\nsg35\nVUse layer size\np49\nsg37\nVuse_layer_size\np50\nstRp51\nag27\n(g28\ng29\n(dp52\ng31\ncexport_layers.builtin_procedures\nautocrop_tagged_layer\np53\nsg33\nVautocrop_background\np54\nsg35\nVAutocrop background\np55\nsg37\ng54\nsg38\n(lp56\n(dp57\ng41\ng42\nsg43\ng44\nsg37\ng45\nsastRp58\nag27\n(g28\ng29\n(dp59\ng31\ng53\nsg33\nVautocrop_foreground\np60\nsg35\nVAutocrop foreground\np61\nsg37\ng60\nsg38\n(lp62\n(dp63\ng41\nVforeground\np64\nsg43\ng44\nsg37\ng45\nsastRp65\nag27\n(g28\ng29\n(dp66\ng31\nNsg33\nVignore_folder_structure\np67\nsg35\nVIgnore folder structure\np68\nsg37\ng67\nstRp69\nag27\n(g28\ng29\n(dp70\ng31\nNsg33\nVuse_file_extensions_in_layer_names\np71\nsg35\nVUse file extensions in layer names\np72\nsg37\ng71\nstRp73\naaa(lp74\nVmain/procedures/_added_data_values\np75\na(dp76\nVinsert_background_layers/display_name\np77\nVInsert background layers\np78\nsVautocrop_foreground/arguments/tag\np79\nVforeground\np80\nsVautocrop_foreground/operation_groups\np81\n(lp82\nVdefault_procedures\np83\nasVinsert_background_layers/operation_groups\np84\n(lp85\ng83\nasVautocrop_foreground/orig_name\np86\ng60\nsVautocrop_background/operation_groups\np87\n(lp88\ng83\nasVuse_file_extensions_in_layer_names/function\np89\nNsVinsert_background_layers/function\np90\ng32\nsVignore_folder_structure/operation_groups\np91\n(lp92\ng83\nasVautocrop_background/enabled\np93\nI01\nsVautocrop_background/display_name\np94\nVAutocrop background\np95\nsVinsert_background_layers/enabled\np96\nI01\nsVignore_folder_structure/enabled\np97\nI01\nsVuse_file_extensions_in_layer_names/enabled\np98\nI01\nsVignore_folder_structure/function\np99\nNsVautocrop_background/orig_name\np100\ng54\nsVuse_file_extensions_in_layer_names/orig_name\np101\ng71\nsVautocrop_foreground/display_name\np102\nVAutocrop foreground\np103\nsVignore_folder_structure/orig_name\np104\ng67\nsVautocrop_foreground/enabled\np105\nI01\nsVuse_layer_size/enabled\np106\nI00\nsVignore_folder_structure/display_name\np107\nVIgnore folder structure\np108\nsVautocrop_background/arguments/tag\np109\nVbackground\np110\nsVinsert_background_layers/arguments/tag\np111\nVbackground\np112\nsVuse_layer_size/operation_groups\np113\n(lp114\ng83\nasVuse_layer_size/orig_name\np115\ng50\nsVautocrop_foreground/function\np116\ng53\nsVautocrop_background/function\np117\ng53\nsVuse_layer_size/function\np118\ng48\nsVuse_file_extensions_in_layer_names/display_name\np119\nVUse file extensions in layer names\np120\nsVuse_file_extensions_in_layer_names/operation_groups\np121\n(lp122\ng83\nasVuse_layer_size/display_name\np123\nVUse layer size\np124\nsVinsert_background_layers/orig_name\np125\ng34\nsaa(lp126\nVmain/constraints/_added_data\np127\na(lp128\ng27\n(g28\ng29\n(dp129\nVfunction\np130\ncexport_layers.builtin_constraints\nis_layer\np131\nsVdisplay_name\np132\nVInclude layers\np133\nsVname\np134\nVinclude_layers\np135\nsVoperation_groups\np136\n(lp137\nVconstraints_layer_types\np138\nasVtype\np139\nVconstraint\np140\nsVsubfilter\np141\nVlayer_types\np142\nstRp143\nag27\n(g28\ng29\n(dp144\ng130\ncexport_layers.builtin_constraints\nis_path_visible\np145\nsVenabled\np146\nI00\nsg139\ng140\nsg134\nVonly_visible_layers\np147\nsg132\nVOnly visible layers\np148\nstRp149\nag27\n(g28\ng29\n(dp150\ng130\ncexport_layers.builtin_constraints\nis_nonempty_group\np151\nsVorig_name\np152\nVinclude_layer_groups\np153\nsg132\nVInclude layer groups\np154\nsg134\ng153\nsg136\n(lp155\ng138\nasg139\ng140\nsg141\ng142\nstRp156\nag27\n(g28\ng29\n(dp157\ng130\ncexport_layers.builtin_constraints\nis_empty_group\np158\nsg152\nVinclude_empty_layer_groups\np159\nsg132\nVInclude empty layer groups\np160\nsg134\ng159\nsg136\n(lp161\ng138\nasg139\ng140\nsg141\ng142\nstRp162\nag27\n(g28\ng29\n(dp163\ng130\ncexport_layers.builtin_constraints\nis_layer_in_selected_layers\np164\nsg152\nVonly_selected_layers\np165\nsg132\nVOnly layers selected in preview\np166\nsg134\ng165\nsg139\ng140\nsVarguments\np167\n(lp168\n(dp169\nVdefault_value\np170\nc__builtin__\nset\np171\n((ltRp172\nsVgui_type\np173\nNsg139\ncexport_layers.pygimplib.pgsetting\nSetting\np174\nsg134\nVselected_layers\np175\nsastRp176\nag27\n(g28\ng29\n(dp177\ng130\ncexport_layers.builtin_constraints\nhas_no_tags\np178\nsg152\nVonly_layers_without_tags\np179\nsg132\nVOnly layers without tags\np180\nsg134\ng179\nsg139\ng140\nsg167\n(lp181\n(dp182\ng170\n(tsVelement_type\np183\ng44\nsg139\ncexport_layers.pygimplib.pgsetting\nArraySetting\np184\nsg134\nVtags\np185\nsastRp186\naaa(lp187\nVmain/constraints/_added_data_values\np188\na(dp189\nVonly_layers_without_tags/enabled\np190\nI01\nsVonly_layers_without_tags/orig_name\np191\ng179\nsVonly_visible_layers/enabled\np192\nI01\nsVonly_visible_layers/display_name\np193\nVOnly visible layers\np194\nsVinclude_layers/display_name\np195\nVInclude layers\np196\nsVonly_layers_without_tags/function\np197\ng178\nsVinclude_layers/operation_groups\np198\n(lp199\ng138\nasVinclude_layers/orig_name\np200\ng135\nsVinclude_empty_layer_groups/display_name\np201\nVInclude empty layer groups\np202\nsVonly_selected_layers/orig_name\np203\ng165\nsVinclude_layer_groups/display_name\np204\nVInclude layer groups\np205\nsVonly_selected_layers/function\np206\ng164\nsVinclude_empty_layer_groups/enabled\np207\nI00\nsVonly_visible_layers/subfilter\np208\nNsVinclude_layers/function\np209\ng131\nsVonly_selected_layers/operation_groups\np210\n(lp211\nVdefault_constraints\np212\nasVonly_selected_layers/subfilter\np213\nNsVinclude_layers/enabled\np214\nI01\nsVinclude_layer_groups/subfilter\np215\ng142\nsVinclude_layers/subfilter\np216\ng142\nsVinclude_layer_groups/operation_groups\np217\n(lp218\ng138\nasVinclude_layer_groups/function\np219\ng151\nsVinclude_layer_groups/enabled\np220\nI00\nsVonly_layers_without_tags/arguments/tags\np221\n(tsVonly_visible_layers/function\np222\ng145\nsVinclude_empty_layer_groups/subfilter\np223\ng142\nsVonly_visible_layers/orig_name\np224\ng147\nsVonly_layers_without_tags/operation_groups\np225\n(lp226\ng212\nasVinclude_layer_groups/orig_name\np227\ng153\nsVinclude_empty_layer_groups/function\np228\ng158\nsVonly_selected_layers/display_name\np229\nVOnly layers selected in preview\np230\nsVonly_selected_layers/enabled\np231\nI01\nsVonly_layers_without_tags/subfilter\np232\nNsVinclude_empty_layer_groups/orig_name\np233\ng159\nsVonly_visible_layers/operation_groups\np234\n(lp235\ng212\nasVonly_layers_without_tags/display_name\np236\nVOnly layers without tags\np237\nsVonly_selected_layers/arguments/selected_layers\np238\n(lp239\nI4\naI6\naI7\naI9\naI10\nasVinclude_empty_layer_groups/operation_groups\np240\n(lp241\ng138\nasaa(lp242\nVgui/dialog_position\np243\na(I516\nI235\ntp244\naa(lp245\nVgui/dialog_size\np246\na(I894\nI685\ntp247\naa(lp248\nVgui/show_more_settings\np249\naI01\naa(lp250\nVgui/paned_outside_previews_position\np251\naI605\naa(lp252\nVgui/paned_between_previews_position\np253\naI416\naa(lp254\nVgui/settings_vpane_position\np255\naI362\naa(lp256\nVgui/name_preview_sensitive\np257\naI01\naa(lp258\nVgui/image_preview_sensitive\np259\naI01\naa(lp260\nVgui/image_preview_automatic_update\np261\naI01\naa(lp262\nVgui/image_preview_automatic_update_if_below_maximum_duration\np263\naI01\naa(lp264\nVmain/selected_layers\np265\naccollections\ndefaultdict\np266\n(g171\ntRp267\nI1\n(lp268\nI4\naI6\naI7\naI9\nasaa(lp269\nVgui_session/image_ids_and_directories\np270\nag27\n(g28\ng29\n(dp271\nI1\nVC:\\u005cUsers\\u005cMyUsername\np272\nstRp273\naa(lp274\nVgui_session/name_preview_layers_collapsed_state\np275\nag266\n(g171\ntRp276\nI1\ng171\n((ltRp277\nsaa(lp278\nVgui_session/image_preview_displayed_layers\np279\nag266\n(cexport_layers.pygimplib.pgutils\nempty_func\np280\ntRp281\nI1\nI7\nsaatRp282\n.'
PERSISTENT_DATA_3_3_1 = b"ccollections\nOrderedDict\np1\n((lp2\n(lp3\nVmain/plugin_version\np4\naV3.3.1\np5\naa(lp6\nVmain/available_tags\np7\na(dp8\nVforeground\np9\nVForeground\np10\nsVbackground\np11\nVBackground\np12\nsaa(lp13\nVmain/file_extension\np14\naVjpg\np15\naa(lp16\nVmain/output_directory\np17\naVC:\\u005cUsers\\u005cMyUsername\np18\naa(lp19\nVmain/layer_filename_pattern\np20\naV[layer name, %e]_[layer path, _]\np21\naa(lp22\nVmain/overwrite_mode\np23\naI2\naa(lp24\nVmain/procedures/_added_data\np25\na(lp26\nccopy_reg\n_reconstructor\np27\n(cfuture.types.newdict\nnewdict\np28\nc__builtin__\ndict\np29\n(dp30\nVfunction\np31\ncexport_layers.builtin_procedures\ninsert_background_layer\np32\nsVorig_name\np33\nVinsert_background_layers\np34\nsVdisplay_name\np35\nVInsert background layers\np36\nsVname\np37\ng34\nsVarguments\np38\n(lp39\n(dp40\nVdefault_value\np41\nVbackground\np42\nsVtype\np43\ncexport_layers.pygimplib.pgsetting\nStringSetting\np44\nsg37\nVtag\np45\nsastRp46\nag27\n(g28\ng29\n(dp47\ng31\ncexport_layers.builtin_procedures\nresize_to_layer_size\np48\nsg35\nVUse layer size\np49\nsg37\nVuse_layer_size\np50\nstRp51\nag27\n(g28\ng29\n(dp52\ng31\ncexport_layers.builtin_procedures\nautocrop_tagged_layer\np53\nsg33\nVautocrop_background\np54\nsg35\nVAutocrop background\np55\nsg37\ng54\nsg38\n(lp56\n(dp57\ng41\ng42\nsg43\ng44\nsg37\ng45\nsastRp58\nag27\n(g28\ng29\n(dp59\ng31\ng53\nsg33\nVautocrop_foreground\np60\nsg35\nVAutocrop foreground\np61\nsg37\ng60\nsg38\n(lp62\n(dp63\ng41\nVforeground\np64\nsg43\ng44\nsg37\ng45\nsastRp65\nag27\n(g28\ng29\n(dp66\ng31\nNsg33\nVignore_folder_structure\np67\nsg35\nVIgnore folder structure\np68\nsg37\ng67\nstRp69\nag27\n(g28\ng29\n(dp70\ng31\nNsg33\nVuse_file_extensions_in_layer_names\np71\nsg35\nVUse file extensions in layer names\np72\nsg37\ng71\nstRp73\naaa(lp74\nVmain/procedures/_added_data_values\np75\na(dp76\nVinsert_background_layers/display_name\np77\nVInsert background layers\np78\nsVautocrop_foreground/arguments/tag\np79\nVforeground\np80\nsVautocrop_foreground/operation_groups\np81\n(lp82\nVdefault_procedures\np83\nasVinsert_background_layers/operation_groups\np84\n(lp85\ng83\nasVautocrop_foreground/orig_name\np86\ng60\nsVautocrop_background/operation_groups\np87\n(lp88\ng83\nasVuse_file_extensions_in_layer_names/function\np89\nNsVinsert_background_layers/function\np90\ng32\nsVignore_folder_structure/operation_groups\np91\n(lp92\ng83\nasVautocrop_background/enabled\np93\nI01\nsVautocrop_background/display_name\np94\nVAutocrop background\np95\nsVinsert_background_layers/enabled\np96\nI01\nsVignore_folder_structure/enabled\np97\nI01\nsVuse_file_extensions_in_layer_names/enabled\np98\nI01\nsVignore_folder_structure/function\np99\nNsVautocrop_background/orig_name\np100\ng54\nsVuse_file_extensions_in_layer_names/orig_name\np101\ng71\nsVautocrop_foreground/display_name\np102\nVAutocrop foreground\np103\nsVignore_folder_structure/orig_name\np104\ng67\nsVautocrop_foreground/enabled\np105\nI01\nsVuse_layer_size/enabled\np106\nI00\nsVignore_folder_structure/display_name\np107\nVIgnore folder structure\np108\nsVautocrop_background/arguments/tag\np109\nVbackground\np110\nsVinsert_background_layers/arguments/tag\np111\nVbackground\np112\nsVuse_layer_size/operation_groups\np113\n(lp114\ng83\nasVuse_layer_size/orig_name\np115\ng50\nsVautocrop_foreground/function\np116\ng53\nsVautocrop_background/function\np117\ng53\nsVuse_layer_size/function\np118\ng48\nsVuse_file_extensions_in_layer_names/display_name\np119\nVUse file extensions in layer names\np120\nsVuse_file_extensions_in_layer_names/operation_groups\np121\n(lp122\ng83\nasVuse_layer_size/display_name\np123\nVUse layer size\np124\nsVinsert_background_layers/orig_name\np125\ng34\nsaa(lp126\nVmain/constraints/_added_data\np127\na(lp128\ng27\n(g28\ng29\n(dp129\nVfunction\np130\ncexport_layers.builtin_constraints\nis_layer\np131\nsVdisplay_name\np132\nVInclude layers\np133\nsVname\np134\nVinclude_layers\np135\nsVoperation_groups\np136\n(lp137\nVconstraints_layer_types\np138\nasVtype\np139\nVconstraint\np140\nsVsubfilter\np141\nVlayer_types\np142\nstRp143\nag27\n(g28\ng29\n(dp144\ng130\ncexport_layers.builtin_constraints\nis_path_visible\np145\nsVenabled\np146\nI00\nsg139\ng140\nsg134\nVonly_visible_layers\np147\nsg132\nVOnly visible layers\np148\nstRp149\nag27\n(g28\ng29\n(dp150\ng130\ncexport_layers.builtin_constraints\nis_nonempty_group\np151\nsVorig_name\np152\nVinclude_layer_groups\np153\nsg132\nVInclude layer groups\np154\nsg134\ng153\nsg136\n(lp155\ng138\nasg139\ng140\nsg141\ng142\nstRp156\nag27\n(g28\ng29\n(dp157\ng130\ncexport_layers.builtin_constraints\nis_empty_group\np158\nsg152\nVinclude_empty_layer_groups\np159\nsg132\nVInclude empty layer groups\np160\nsg134\ng159\nsg136\n(lp161\ng138\nasg139\ng140\nsg141\ng142\nstRp162\nag27\n(g28\ng29\n(dp163\ng130\ncexport_layers.builtin_constraints\nis_layer_in_selected_layers\np164\nsg152\nVonly_selected_layers\np165\nsg132\nVOnly layers selected in preview\np166\nsg134\ng165\nsg139\ng140\nsVarguments\np167\n(lp168\n(dp169\nVdefault_value\np170\nc__builtin__\nset\np171\n((ltRp172\nsVgui_type\np173\nNsg139\ncexport_layers.pygimplib.pgsetting\nSetting\np174\nsg134\nVselected_layers\np175\nsastRp176\nag27\n(g28\ng29\n(dp177\ng130\ncexport_layers.builtin_constraints\nhas_no_tags\np178\nsg152\nVonly_layers_without_tags\np179\nsg132\nVOnly layers without tags\np180\nsg134\ng179\nsg139\ng140\nsg167\n(lp181\n(dp182\ng170\n(tsVelement_type\np183\ng44\nsg139\ncexport_layers.pygimplib.pgsetting\nArraySetting\np184\nsg134\nVtags\np185\nsastRp186\naaa(lp187\nVmain/constraints/_added_data_values\np188\na(dp189\nVonly_layers_without_tags/enabled\np190\nI01\nsVonly_layers_without_tags/orig_name\np191\ng179\nsVonly_visible_layers/enabled\np192\nI01\nsVonly_visible_layers/display_name\np193\nVOnly visible layers\np194\nsVinclude_layers/display_name\np195\nVInclude layers\np196\nsVonly_layers_without_tags/function\np197\ng178\nsVinclude_layers/operation_groups\np198\n(lp199\ng138\nasVinclude_layers/orig_name\np200\ng135\nsVinclude_empty_layer_groups/display_name\np201\nVInclude empty layer groups\np202\nsVonly_selected_layers/orig_name\np203\ng165\nsVinclude_layer_groups/display_name\np204\nVInclude layer groups\np205\nsVonly_selected_layers/function\np206\ng164\nsVinclude_empty_layer_groups/enabled\np207\nI00\nsVonly_visible_layers/subfilter\np208\nNsVinclude_layers/function\np209\ng131\nsVonly_selected_layers/operation_groups\np210\n(lp211\nVdefault_constraints\np212\nasVonly_selected_layers/subfilter\np213\nNsVinclude_layers/enabled\np214\nI01\nsVinclude_layer_groups/subfilter\np215\ng142\nsVinclude_layers/subfilter\np216\ng142\nsVinclude_layer_groups/operation_groups\np217\n(lp218\ng138\nasVinclude_layer_groups/function\np219\ng151\nsVinclude_layer_groups/enabled\np220\nI00\nsVonly_layers_without_tags/arguments/tags\np221\n(tsVonly_visible_layers/function\np222\ng145\nsVinclude_empty_layer_groups/subfilter\np223\ng142\nsVonly_visible_layers/orig_name\np224\ng147\nsVonly_layers_without_tags/operation_groups\np225\n(lp226\ng212\nasVinclude_layer_groups/orig_name\np227\ng153\nsVinclude_empty_layer_groups/function\np228\ng158\nsVonly_selected_layers/display_name\np229\nVOnly layers selected in preview\np230\nsVonly_selected_layers/enabled\np231\nI01\nsVonly_layers_without_tags/subfilter\np232\nNsVinclude_empty_layer_groups/orig_name\np233\ng159\nsVonly_visible_layers/operation_groups\np234\n(lp235\ng212\nasVonly_layers_without_tags/display_name\np236\nVOnly layers without tags\np237\nsVonly_selected_layers/arguments/selected_layers\np238\n(lp239\nI4\naI6\naI7\naI9\naI10\nasVinclude_empty_layer_groups/operation_groups\np240\n(lp241\ng138\nasaa(lp242\nVgui/dialog_position\np243\na(I516\nI235\ntp244\naa(lp245\nVgui/dialog_size\np246\na(I894\nI685\ntp247\naa(lp248\nVgui/show_more_settings\np249\naI01\naa(lp250\nVgui/paned_outside_previews_position\np251\naI605\naa(lp252\nVgui/paned_between_previews_position\np253\naI416\naa(lp254\nVgui/settings_vpane_position\np255\naI362\naa(lp256\nVgui/name_preview_sensitive\np257\naI01\naa(lp258\nVgui/image_preview_sensitive\np259\naI01\naa(lp260\nVgui/image_preview_automatic_update\np261\naI01\naa(lp262\nVgui/image_preview_automatic_update_if_below_maximum_duration\np263\naI01\naa(lp264\nVmain/selected_layers_persistent\np265\naccollections\ndefaultdict\np266\n(g171\ntRp267\nS'C:\\\\Users\\\\MyUsername\\\\test_export_layers\\\\test_export_layers_contents.xcf'\np268\ng171\n((lp269\nVtop-frame\np270\naVleft-frame\np271\naVbottom-frame\np272\naVright-frame\np273\natRp274\nsaa(lp275\nVgui_persistent/name_preview_layers_collapsed_state\np276\nag266\n(g171\ntRp277\nS'C:\\\\Users\\\\MyUsername\\\\test_export_layers\\\\test_export_layers_contents.xcf'\np278\ng171\n((ltRp279\nsaa(lp280\nVgui_persistent/image_preview_displayed_layers\np281\nag266\n(cexport_layers.pygimplib.pgutils\nempty_func\np282\ntRp283\nS'C:\\\\Users\\\\MyUsername\\\\test_export_layers\\\\test_export_layers_contents.xcf'\np284\ng273\nsaatRp285\n."

DATA_3_3_1_PLUGIN_VERSION_AND_TAGS_ONLY = b'ccollections\nOrderedDict\np1\n((lp2\n(lp3\nVmain/plugin_version\np4\naV3.3.1\np5\naa(lp6\nVmain/available_tags\np7\na(dp8\nVforeground\np9\nVForeground\np10\nsVbackground\np11\nVBackground\np12\nsaatRp13\n.'

VERSION_TO_UPDATE_TO = '4.0'

EXPECTED_PROCEDURE_ATTRIBUTES_FOR_FULL_DATA = [
  {
    'name': 'insert_background_layers',
    'orig_name': 'insert_background_layers',
    'enabled': True,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_PROCEDURES_GROUP],
    'arguments': [
      {
        'name': 'tag',
        'value': 'background',
      },
    ],
  },
  {
    'name': 'use_layer_size',
    'orig_name': 'use_layer_size',
    'enabled': False,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_PROCEDURES_GROUP],
    'arguments': [],
  },
  {
    'name': 'plug_in_autocrop_layer',
    'orig_name': 'plug_in_autocrop_layer',
    'display_name': 'Autocrop background',
    'enabled': True,
    'function': 'plug_in_autocrop_layer',
    'origin': 1,
    'action_groups': [actions_.DEFAULT_PROCEDURES_GROUP],
    'arguments': [
      {
        'name': 'run-mode',
        'value': 1,
      },
      {
        'name': 'image',
        'value': 'current_image',
      },
      {
        'name': 'drawable',
        'value': 'background_layer',
      },
    ],
  },
  {
    'name': 'plug_in_autocrop_layer_2',
    'orig_name': 'plug_in_autocrop_layer',
    'display_name': 'Autocrop foreground',
    'enabled': True,
    'function': 'plug_in_autocrop_layer',
    'origin': 1,
    'action_groups': [actions_.DEFAULT_PROCEDURES_GROUP],
    'arguments': [
      {
        'name': 'run-mode',
        'value': 1,
      },
      {
        'name': 'image',
        'value': 'current_image',
      },
      {
        'name': 'drawable',
        'value': 'foreground_layer',
      },
    ],
  },
  {
    'name': 'ignore_folder_structure',
    'orig_name': 'ignore_folder_structure',
    'enabled': True,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_PROCEDURES_GROUP],
    'arguments': [],
  },
  {
    'name': 'export',
    'orig_name': 'export',
    'enabled': True,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_PROCEDURES_GROUP],
    'arguments': [
      {
        'name': 'output_directory',
        'value': 'C:\\Users\\MyUsername',
      },
      {
        'name': 'file_extension',
        'value': 'jpg',
      },
      {
        'name': 'export_mode',
        'value': export_.ExportModes.EACH_LAYER,
      },
      {
        'name': 'single_image_filename_pattern',
        'value': '[image name]',
      },
      {
        'name': 'use_file_extension_in_item_name',
        'value': True,
      },
      {
        'name': 'convert_file_extension_to_lowercase',
        'value': False,
      },
      {
        'name': 'preserve_layer_name_after_export',
        'value': False,
      },
    ],
  },
]

EXPECTED_CONSTRAINT_ATTRIBUTES_FOR_FULL_DATA = [
  {
    'name': 'visible',
    'orig_name': 'visible',
    'enabled': True,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_CONSTRAINTS_GROUP],
    'arguments': [],
    'also_apply_to_parent_folders': True,
  },
  {
    'name': 'layers',
    'orig_name': 'layers',
    'enabled': True,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_CONSTRAINTS_GROUP],
    'arguments': [],
    'also_apply_to_parent_folders': False,
  },
  {
    'name': 'selected_in_preview',
    'orig_name': 'selected_in_preview',
    'enabled': True,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_CONSTRAINTS_GROUP],
    'arguments': [
      {
        'name': 'selected_layers',
        'value': set(),
      }
    ],
    'also_apply_to_parent_folders': False,
  },
  {
    'name': 'without_tags',
    'orig_name': 'without_tags',
    'enabled': True,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_CONSTRAINTS_GROUP],
    'arguments': [
      {
        'name': 'tags',
        'value': (),
      }
    ],
    'also_apply_to_parent_folders': False,
  },
]

EXPECTED_PROCEDURE_ATTRIBUTES_FOR_PARTIAL_DATA = [
  {
    'name': 'use_layer_size',
    'orig_name': 'use_layer_size',
    'enabled': True,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_PROCEDURES_GROUP],
    'arguments': [],
  },
]

EXPECTED_CONSTRAINT_ATTRIBUTES_FOR_PARTIAL_DATA = [
  {
    'name': 'layers',
    'orig_name': 'layers',
    'enabled': True,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_CONSTRAINTS_GROUP],
    'arguments': [],
    'also_apply_to_parent_folders': False,
  },
  {
    'name': 'visible',
    'orig_name': 'visible',
    'enabled': False,
    'function': '',
    'origin': 0,
    'action_groups': [actions_.DEFAULT_CONSTRAINTS_GROUP],
    'arguments': [],
    'also_apply_to_parent_folders': True,
  },
]


REMOVED_ACTION_SETTINGS = ['subfilter', 'is_pdb_procedure', 'operation_groups']


@mock.patch('export_layers.update._remove_obsolete_pygimplib_files_3_3_2')
@mock.patch('export_layers.update._remove_obsolete_plugin_files_3_3_2')
@mock.patch('export_layers.update._try_remove_file')
class TestUpdateFrom331To34(unittest.TestCase):
  
  def setUp(self):
    self.gimp_module = stubs_gimp.GimpModuleStub()
    self.shelf = stubs_gimp.ShelfStub(shelf=self.gimp_module.shelf_data)
    
    self.sources_gimp_patcher = mock.patch(
      pg.utils.get_pygimplib_module_path() + '.setting.sources.gimp', new=self.gimp_module)
    self.mock_sources_gimp = self.sources_gimp_patcher.start()
    
    self.sources_shelf_patcher = mock.patch(
      pg.utils.get_pygimplib_module_path() + '.setting.sources.gimpshelf.shelf', new=self.shelf)
    self.mock_sources_shelf = self.sources_shelf_patcher.start()
    
    self.update_gimp_patcher = mock.patch('export_layers.update.gimp', new=self.gimp_module)
    self.mock_update_gimp = self.update_gimp_patcher.start()
    
    self.update_shelf_patcher = mock.patch('export_layers.update.gimpshelf.shelf', new=self.shelf)
    self.mock_update_shelf = self.update_shelf_patcher.start()
    
    self.orig_version_in_config = pg.config.PLUGIN_VERSION
    pg.config.PLUGIN_VERSION = VERSION_TO_UPDATE_TO
    
    self.settings = settings_main.create_settings()
    
    self.maxDiff = None
  
  def tearDown(self):
    self.sources_gimp_patcher.stop()
    self.sources_shelf_patcher.stop()
    self.update_gimp_patcher.stop()
    self.update_shelf_patcher.stop()
    
    pg.config.PLUGIN_VERSION = self.orig_version_in_config
  
  def test_no_data_in_sources_saves_plugin_version_only(self, *mocks):
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.FRESH_START)
    self.assertEqual(self.settings['main/plugin_version'].value, pg.config.PLUGIN_VERSION)
    
    expected_data = [
      {
        'name': 'all_settings',
        'settings': [{
          'name': 'main',
          'setting_attributes': {'setting_sources': ['session', 'persistent']},
          'settings': [
            {
              'name': 'plugin_version',
              'type': 'string',
              'default_value': pg.config.PLUGIN_VERSION,
              'value': pg.config.PLUGIN_VERSION,
              'pdb_type': None,
              'gui_type': None,
              'setting_sources': ['session', 'persistent'],
            }
          ]
        }],
      }
    ]
    
    self.assertListEqual(update.gimpshelf.shelf[pg.config.SOURCE_NAME], expected_data)
    
    self.assertListEqual(
      pickle.loads(update.gimp.parasite_find(pg.config.SOURCE_NAME).data), expected_data)
  
  def test_partial_data_in_session_source_only(self, *mocks):
    update.gimp.set_data(pg.config.SOURCE_NAME, DATA_3_3_1_PLUGIN_VERSION_AND_TAGS_ONLY)
    
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.UPDATE)
    
    self._test_update_for_partial_data(is_selected_layers_nonempty=False)
  
  def test_partial_data_in_persistent_source_only(self, *mocks):
    update.gimp.parasite_attach(
      update.gimp.Parasite(
        pg.config.SOURCE_NAME,
        gimpenums.PARASITE_PERSISTENT,
        DATA_3_3_1_PLUGIN_VERSION_AND_TAGS_ONLY))
    
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.UPDATE)
    
    self._test_update_for_partial_data(is_selected_layers_nonempty=False)
  
  def test_partial_data_in_session_and_persistent_source(self, *mocks):
    update.gimp.parasite_attach(
      update.gimp.Parasite(
        pg.config.SOURCE_NAME,
        gimpenums.PARASITE_PERSISTENT,
        DATA_3_3_1_PLUGIN_VERSION_AND_TAGS_ONLY))
    
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.UPDATE)
    
    self._test_update_for_partial_data(is_selected_layers_nonempty=False)
  
  def test_full_data_in_session_source_only(self, *mocks):
    update.gimp.set_data(pg.config.SOURCE_NAME, SESSION_DATA_3_3_1)
    
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.UPDATE)
    
    self._test_update_for_full_data(is_selected_layers_nonempty=True)
  
  def test_full_data_in_persistent_source_only(self, *mocks):
    update.gimp.parasite_attach(
      update.gimp.Parasite(
        pg.config.SOURCE_NAME, gimpenums.PARASITE_PERSISTENT, PERSISTENT_DATA_3_3_1))
    
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.UPDATE)
    
    self._test_update_for_full_data(is_selected_layers_nonempty=False)
  
  def test_full_data_in_session_and_persistent_source(self, *mocks):
    update.gimp.set_data(pg.config.SOURCE_NAME, SESSION_DATA_3_3_1)
    update.gimp.parasite_attach(
      update.gimp.Parasite(
        pg.config.SOURCE_NAME, gimpenums.PARASITE_PERSISTENT, PERSISTENT_DATA_3_3_1))
    
    status, unused_ = update.update(self.settings)
    
    self.assertEqual(status, update.UPDATE)
    
    self._test_update_for_full_data(is_selected_layers_nonempty=True)
  
  def _test_update_for_partial_data(self, is_selected_layers_nonempty):
    self._test_lengths_of_groups()
    
    self._test_selected_and_collapsed_settings(is_selected_layers_nonempty)
    
    self._test_contents_of_procedures_for_partial_data()
    self._test_contents_of_constraints_for_partial_data()
  
  def _test_contents_of_procedures_for_partial_data(self):
    self._test_contents_of_actions(
      self.settings['main/procedures'], EXPECTED_PROCEDURE_ATTRIBUTES_FOR_PARTIAL_DATA)
  
  def _test_contents_of_constraints_for_partial_data(self):
    self._test_contents_of_actions(
      self.settings['main/constraints'], EXPECTED_CONSTRAINT_ATTRIBUTES_FOR_PARTIAL_DATA)
  
  def _test_update_for_full_data(self, is_selected_layers_nonempty):
    self._test_lengths_of_groups()
    
    self._test_selected_and_collapsed_settings(is_selected_layers_nonempty)
    
    self._test_contents_of_procedures_for_full_data()
    self._test_contents_of_constraints_for_full_data()
    self._test_main_settings_for_full_data()
  
  def _test_lengths_of_groups(self):
    self._test_length_and_names_of_settings(self.settings, ORIG_SETTINGS)
    self._test_length_and_names_of_settings(self.settings['special'], ORIG_SETTINGS['special'])
    self._test_length_and_names_of_settings(self.settings['main'], ORIG_SETTINGS['main'])
    self._test_length_and_names_of_settings(self.settings['gui'], ORIG_SETTINGS['gui'])
    self._test_length_and_names_of_settings(self.settings['gui/size'], ORIG_SETTINGS['gui/size'])
  
  def _test_main_settings_for_full_data(self):
    self.assertEqual(self.settings['main/plugin_version'].value, pg.config.PLUGIN_VERSION)
    self.assertEqual(self.settings['main/output_directory'].value, 'C:\\Users\\MyUsername')
    self.assertEqual(self.settings['main/file_extension'].value, 'jpg')
    self.assertEqual(
      self.settings['main/layer_filename_pattern'].value,
      '[layer name, %e]_[layer path, _, %c, %e]')
  
  def _test_selected_and_collapsed_settings(self, is_selected_layers_nonempty):
    self.assertEqual(
      bool(self.settings['main/selected_layers'].value), is_selected_layers_nonempty)
    self.assertFalse(self.settings['gui/name_preview_layers_collapsed_state'].value)
    self.assertFalse(self.settings['gui/image_preview_displayed_layers'].value)
  
  def _test_contents_of_procedures_for_full_data(self):
    self._test_contents_of_actions(
      self.settings['main/procedures'], EXPECTED_PROCEDURE_ATTRIBUTES_FOR_FULL_DATA)
  
  def _test_contents_of_constraints_for_full_data(self):
    self._test_contents_of_actions(
      self.settings['main/constraints'], EXPECTED_CONSTRAINT_ATTRIBUTES_FOR_FULL_DATA)
  
  def _test_contents_of_actions(self, actions, expected_action_attributes):
    self.assertEqual(len(actions), len(expected_action_attributes))
    
    for expected_attributes_per_action, action in zip(expected_action_attributes, actions):
      for setting_name, setting_value in expected_attributes_per_action.items():
        if setting_name == 'name':
          self.assertEqual(action.name, setting_value)
        elif setting_name == 'arguments':
          for argument_dict in setting_value:
            argument_name = argument_dict['name']
            argument_value = argument_dict['value']
            self.assertEqual(action['arguments/' + argument_name].value, argument_value)
        else:
          self.assertEqual(action[setting_name].value, setting_value)
    
    self.assertNotIn('added', actions)
    self.assertNotIn('_added_data', actions)
    self.assertNotIn('_added_data_values', actions)
    
    for action in actions:
      for setting_name in REMOVED_ACTION_SETTINGS:
        self.assertNotIn(setting_name, action)
  
  def _test_length_and_names_of_settings(self, actual_settings, expected_settings):
    self.assertEqual(len(actual_settings), len(expected_settings))
    for actual_child, expected_child in zip(actual_settings, expected_settings):
      self.assertEqual(actual_child.name, expected_child.name)


class TestUpdateConstraintsIn34(unittest.TestCase):
  
  def test_update_with_include_layers(self):
    constraints = actions_.create('constraints')
    
    actions_.add(
      constraints, {'name': 'include_layers', 'type': 'constraint', 'enabled': True})
    
    update._update_include_constraints(constraints)
    
    self.assertEqual(len(constraints), 1)
    self.assertIn('layers', constraints)
    self.assertTrue(constraints['layers/enabled'].value)
  
  def test_update_with_disabled_include_layers(self):
    constraints = actions_.create('constraints')
    
    actions_.add(
      constraints, {'name': 'include_layers', 'type': 'constraint', 'enabled': False})
    
    update._update_include_constraints(constraints)
    
    self.assertEqual(len(constraints), 2)
    self.assertIn('layers', constraints)
    self.assertTrue(constraints['layers/enabled'].value)
    
    self.assertIn('layer_groups', constraints)
    self.assertTrue(constraints['layer_groups/enabled'].value)
  
  def test_update_with_include_layer_groups(self):
    constraints = actions_.create('constraints')
    
    actions_.add(
      constraints, {'name': 'include_layer_groups', 'type': 'constraint', 'enabled': True})
    
    update._update_include_constraints(constraints)
    
    self.assertEqual(len(constraints), 1)
    self.assertIn('layer_groups', constraints)
    self.assertTrue(constraints['layer_groups/enabled'].value)
  
  def test_update_with_disabled_include_layer_groups(self):
    constraints = actions_.create('constraints')
    
    actions_.add(
      constraints, {'name': 'include_layer_groups', 'type': 'constraint', 'enabled': False})
    
    update._update_include_constraints(constraints)
    
    self.assertEqual(len(constraints), 2)
    self.assertIn('layers', constraints)
    self.assertTrue(constraints['layers/enabled'].value)
    
    self.assertIn('layer_groups', constraints)
    self.assertTrue(constraints['layer_groups/enabled'].value)
  
  def test_update_with_include_layers_and_disabled_layer_groups(self):
    constraints = actions_.create('constraints')
    
    actions_.add(
      constraints, {'name': 'include_layers', 'type': 'constraint', 'enabled': True})
    actions_.add(
      constraints, {'name': 'include_layer_groups', 'type': 'constraint', 'enabled': False})
    
    update._update_include_constraints(constraints)
    
    self.assertEqual(len(constraints), 1)
    self.assertIn('layers', constraints)
    self.assertTrue(constraints['layers/enabled'].value)
  
  def test_update_with_include_layers_and_enabled_layer_groups(self):
    constraints = actions_.create('constraints')
    
    actions_.add(
      constraints, {'name': 'include_layers', 'type': 'constraint', 'enabled': True})
    actions_.add(
      constraints, {'name': 'include_layer_groups', 'type': 'constraint', 'enabled': True})
    
    update._update_include_constraints(constraints)
    
    self.assertEqual(len(constraints), 0)
