# -*- coding: utf-8 -*-
"""
Created on Thu Nov 28 08:29:18 2019

@author: evand
"""

import sys
import getopt
import os
from gerber import load_layer
from gerber.render import RenderSettings, theme
from gerber.render.cairo_backend import GerberCairoContext
from PIL import Image
import configparser


def isrendercurrent(BASE_FOLDER):
    if not (os.path.exists(os.path.join(BASE_FOLDER, 'board_top.png')) and
             os.path.exists(os.path.join(BASE_FOLDER, 'board_bottom.png')) and
             os.path.exists(os.path.join(BASE_FOLDER, 'board.ini'))):
        return False

    config = configparser.ConfigParser()
    config.read(os.path.join(BASE_FOLDER, 'board.ini'))

    mtime = 0
    for filename in os.listdir(os.path.join(BASE_FOLDER, 'GerberFiles')):
        mtime = max(mtime, os.path.getmtime(os.path.join(BASE_FOLDER, 'GerberFiles', filename)))
    ini_mtime = float(config['OTHER']['GERBERS_LASTMODIFIED'])
    if mtime == ini_mtime:
        return True
    else:
        return False


def render(BASE_FOLDER):
    ppi = 1000
    # font_size_in = 0.02
    # font_color = 'rgb(255, 0, 0)'
    # textbox_color = "skyblue"
    Image.MAX_IMAGE_PIXELS = 1000000000

    if os.path.exists(os.path.join(BASE_FOLDER, 'board_top.png')):
        os.remove(os.path.join(BASE_FOLDER, 'board_top.png'))
    if os.path.exists(os.path.join(BASE_FOLDER, 'board_bottom.png')):
        os.remove(os.path.join(BASE_FOLDER, 'board_bottom.png'))

    print('Processing ', BASE_FOLDER)

    # Open the gerber files
    copper = load_layer(os.path.join(BASE_FOLDER, 'GerberFiles\copper_top.gbr'))
    mask = load_layer(os.path.join(BASE_FOLDER, 'GerberFiles\soldermask_top.gbr'))
    silk = load_layer(os.path.join(BASE_FOLDER, 'GerberFiles\silkscreen_top.gbr'))
    outline = load_layer(os.path.join(BASE_FOLDER, 'GerberFiles\profile.gbr'))
    drill = load_layer(os.path.join(BASE_FOLDER, 'DrillFiles\drill_1_16.xln'))

    # Create a new drawing context
    ctx = GerberCairoContext(scale=ppi)

    # Draw the outline first, so it establishes the outer dimensions
    ctx.render_layer(outline, settings=RenderSettings(color=theme.COLORS['black'], alpha=0.85))

    # Draw the copper layer. render_layer() uses the default color scheme for the
    # layer, based on the layer type. Copper layers are rendered as
    ctx.render_layer(copper, settings=RenderSettings(color=theme.COLORS['hasl copper'], alpha=0.85))

    # Draw the soldermask layer
    ctx.render_layer(mask, settings=RenderSettings(color=theme.COLORS['green soldermask'], invert=True, alpha=0.8))

    # Draw the silkscreen layer, and specify the rendering settings to use
    ctx.render_layer(silk, settings=RenderSettings(color=theme.COLORS['white'], alpha=0.85))

    # Draw the drill layer
    ctx.render_layer(drill)

    # Draw the outline again so it's on top of everything
    ctx.render_layer(outline, settings=RenderSettings(color=theme.COLORS['black'], alpha=0.85))

    size_px = ctx.size_in_pixels
    origin_px = ctx.origin_in_pixels
    origin_in = ctx.origin_in_inch
    print(f"size: {ctx.size_in_inch} in / {ctx.size_in_pixels} px ({ppi} PPI)")
    print(f"origin: {ctx.origin_in_inch} in / {ctx.origin_in_pixels} px")
    config = configparser.ConfigParser()
    config['DIMENSIONS'] = {'SIZE_X_IN': ctx.size_in_inch[0],
                            'SIZE_Y_IN': ctx.size_in_inch[1],
                            'SIZE_X_PX': ctx.size_in_pixels[0],
                            'SIZE_Y_PX': ctx.size_in_pixels[1],
                            'PPI': ppi,
                            'ORIGIN_X_IN': ctx.origin_in_inch[0],
                            'ORIGIN_Y_IN': ctx.origin_in_inch[1]}

    mtime = 0
    for filename in os.listdir(os.path.join(BASE_FOLDER, 'GerberFiles')):
        mtime = max(mtime, os.path.getmtime(os.path.join(BASE_FOLDER, 'GerberFiles',filename)))
    print('Latest file modification time: ', mtime)
    config['OTHER'] = {'GERBERS_LASTMODIFIED': mtime}
    with open(os.path.join(BASE_FOLDER,'board.ini'),'w') as configfile:
        config.write(configfile)

    # Write output to png file
    ctx.dump(os.path.join(BASE_FOLDER, 'board_top.png'), verbose=True)

    # Load the bottom layers
    copper = load_layer(os.path.join(BASE_FOLDER, 'GerberFiles\copper_bottom.gbr'))
    mask = load_layer(os.path.join(BASE_FOLDER, 'GerberFiles\soldermask_bottom.gbr'))
    silk = load_layer(os.path.join(BASE_FOLDER, 'GerberFiles\silkscreen_bottom.gbr'))

    # Clear the drawing
    ctx.clear()

    # Render bottom layers
    ctx.render_layer(outline, settings=RenderSettings(color=theme.COLORS['black'], mirror=True, alpha=0.85))
    ctx.render_layer(copper, settings=RenderSettings(color=theme.COLORS['hasl copper'], alpha=0.85))
    ctx.render_layer(mask, settings=RenderSettings(color=theme.COLORS['green soldermask'], invert=True, alpha=0.8))
    ctx.render_layer(silk, settings=RenderSettings(color=theme.COLORS['white'], alpha=0.85))
    ctx.render_layer(drill)
    ctx.render_layer(outline, settings=RenderSettings(color=theme.COLORS['black'], mirror=True, alpha=0.85))

    # Write png file
    ctx.dump(os.path.join(BASE_FOLDER, 'board_bottom.png'), verbose=True)


if __name__ == "__main__":
    BASE_FOLDER = './'
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:o:")
    except getopt.GetoptError:
        print('gerber_pnp_vis.py -i <inputdir>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-i":
            BASE_FOLDER = arg
    render(BASE_FOLDER)