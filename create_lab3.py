#!/usr/bin/env python3
"""
Create Lab3 Sans font family.

Base: Inter
Replacement from Source Sans 3:
  - g (2-storey g from Source Sans 3)
"""

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.misc.transform import Transform
import os
import glob

print("="*70)
print("Creating Lab3 Sans Font Family")
print("="*70)

# Find available fonts
print("\nStep 1: Finding available font files...")
print("-"*70)

def find_fonts(base_path, pattern):
    """Find all matching font files."""
    return sorted(glob.glob(os.path.join(base_path, pattern)))

# Look for fonts
inter_fonts = find_fonts('fonts/fonts', 'Inter-*.ttf')
source_sans_fonts = find_fonts('fonts/fonts', 'SourceSans3-*.ttf')

print(f"\nFound {len(inter_fonts)} Inter fonts")
print(f"Found {len(source_sans_fonts)} Source Sans 3 fonts")

# Map weight names
weight_mapping = {
    'ExtraLight': ('ExtraLight', 200),
    'Light': ('Light', 300),
    'Regular': ('Regular', 400),
    'Medium': ('Medium', 500),
    'Semibold': ('SemiBold', 600),
    'Bold': ('Bold', 700),
    'Black': ('Black', 900),
}

def parse_font_name(path):
    """Extract weight and style from font filename."""
    basename = os.path.basename(path)
    name_without_ext = basename.replace('.ttf', '')

    # Remove font family prefix
    if name_without_ext.startswith('SourceSans3-'):
        weight_style = name_without_ext.replace('SourceSans3-', '')
    elif name_without_ext.startswith('Inter-'):
        weight_style = name_without_ext.replace('Inter-', '')
    else:
        return None, None

    # Check for italic (check longer suffix first to avoid partial matches)
    if weight_style.endswith('Italic'):
        is_italic = True
        weight = weight_style[:-6]  # Remove 'Italic'
    elif weight_style.endswith('It'):
        is_italic = True
        weight = weight_style[:-2]  # Remove 'It'
    else:
        is_italic = False
        weight = weight_style

    # Empty weight means "Regular"
    if weight == '':
        weight = 'Regular'

    return weight, is_italic

# Match fonts by weight
print("\nStep 2: Matching fonts by weight...")
print("-"*70)

font_pairs = []
for inter_path in inter_fonts:
    inter_weight, inter_italic = parse_font_name(inter_path)
    if not inter_weight:
        continue

    # Find matching Source Sans 3 font
    for ss_path in source_sans_fonts:
        ss_weight, ss_italic = parse_font_name(ss_path)
        if not ss_weight:
            continue

        # Match weight and style
        if inter_weight.lower() == ss_weight.lower() and inter_italic == ss_italic:
            font_pairs.append({
                'weight': inter_weight,
                'italic': inter_italic,
                'inter': inter_path,
                'source_sans': ss_path
            })
            style_str = "Italic" if inter_italic else "Regular"
            print(f"  ✓ {inter_weight:12s} {style_str:7s}: Matched")
            break

print(f"\nTotal matched pairs: {len(font_pairs)}")

if len(font_pairs) == 0:
    print("\n✗ No matching font pairs found!")
    exit(1)

# Step 3: Process each font pair
print("\nStep 3: Processing font pairs...")
print("="*70)

def copy_and_scale_glyph(target_font, source_font, source_glyph_name, target_glyph_name,
                         reference_glyph_name='g'):
    """
    Copy a glyph from source to target, scaling to match target glyph's original dimensions.

    Width: Match the target glyph's original width (preserve design intent)
    Height: Use reference glyph for vertical alignment (use 'g' itself for proper descender depth)
    Metrics: Preserve target glyph's original advance/LSB (preserve spacing)
    """
    # Get the target glyph's ORIGINAL dimensions and metrics
    target_glyph_orig = target_font['glyf'][target_glyph_name]
    target_width = target_glyph_orig.xMax - target_glyph_orig.xMin
    target_advance, target_lsb = target_font['hmtx'][target_glyph_name]

    # Get reference for vertical dimensions (use 'g' itself to preserve descender depth)
    ref_glyph = target_font['glyf'][reference_glyph_name]
    ref_height = ref_glyph.yMax - ref_glyph.yMin
    ref_yMin = ref_glyph.yMin
    ref_yMax = ref_glyph.yMax

    # Get source glyph
    source_glyphset = source_font.getGlyphSet()
    source_glyph = source_font['glyf'][source_glyph_name]

    source_width = source_glyph.xMax - source_glyph.xMin
    source_height = source_glyph.yMax - source_glyph.yMin

    # Calculate scale factors
    # Horizontal: match target glyph's original width
    # Vertical: match reference height for proper alignment
    scale_x = target_width / source_width
    scale_y = ref_height / source_height

    # Decompose source glyph
    recording_pen = DecomposingRecordingPen(source_glyphset)
    source_glyphset[source_glyph_name].draw(recording_pen)

    # Create transform
    transform = Transform()
    transform = transform.scale(scale_x, scale_y)

    # Calculate translation
    # Horizontal: align to target glyph's original position
    # Vertical: align bottom to ref_yMin
    translate_x = target_glyph_orig.xMin - (source_glyph.xMin * scale_x)
    translate_y = ref_yMin - (source_glyph.yMin * scale_y)
    transform = transform.translate(translate_x, translate_y)

    # Create new glyph
    glyph_pen = TTGlyphPen(target_font.getGlyphSet())
    recording_pen.replay(glyph_pen)
    new_glyph = glyph_pen.glyph()

    # Apply transform to coordinates
    if hasattr(new_glyph, 'coordinates') and new_glyph.coordinates:
        coords = new_glyph.coordinates
        new_coords = []
        for x, y in coords:
            tx, ty = transform.transformPoint((x, y))
            new_coords.append((int(round(tx)), int(round(ty))))

        # Calculate current bounds from rounded coordinates
        xs = [x for x, y in new_coords]
        ys = [y for x, y in new_coords]
        current_yMin = min(ys)
        current_yMax = max(ys)

        # Adjust coordinates to match exact reference bounds
        # Find how much we need to shift to align bounds perfectly
        yMin_offset = ref_yMin - current_yMin
        yMax_offset = ref_yMax - current_yMax

        # Adjust all y-coordinates: shift bottom points by yMin_offset, top by yMax_offset
        # For points in between, interpolate
        adjusted_coords = []
        for x, y in new_coords:
            if y == current_yMin:
                # Bottom-most points: align to ref_yMin
                new_y = ref_yMin
            elif y == current_yMax:
                # Top-most points: align to ref_yMax
                new_y = ref_yMax
            else:
                # Interpolate adjustment based on position
                if current_yMax != current_yMin:
                    ratio = (y - current_yMin) / (current_yMax - current_yMin)
                    offset = yMin_offset + (yMax_offset - yMin_offset) * ratio
                    new_y = y + int(round(offset))
                else:
                    new_y = y
            adjusted_coords.append((x, new_y))

        # Update glyph coordinates
        new_glyph.coordinates = GlyphCoordinates(adjusted_coords)

        # Update bounds
        xs = [x for x, y in adjusted_coords]
        ys = [y for x, y in adjusted_coords]
        new_glyph.xMin = min(xs)
        new_glyph.xMax = max(xs)
        new_glyph.yMin = min(ys)
        new_glyph.yMax = max(ys)

        # Ensure xMin matches LSB for correct horizontal positioning
        x_offset = target_lsb - new_glyph.xMin
        if x_offset != 0:
            # Shift all x-coordinates
            final_coords = [(x + x_offset, y) for x, y in adjusted_coords]
            new_glyph.coordinates = GlyphCoordinates(final_coords)
            new_glyph.xMin += x_offset
            new_glyph.xMax += x_offset

    # Replace in target font
    target_font['glyf'][target_glyph_name] = new_glyph

    # Set advance width to make RSB = 30 units
    # Formula: RSB = advance - lsb - width
    # If RSB = 30, then: advance = lsb + width + 30
    target_rsb = 30
    adjusted_advance = target_lsb + target_width + target_rsb

    # Set metrics with adjusted advance width and original LSB
    target_font['hmtx'][target_glyph_name] = (adjusted_advance, target_lsb)

    return {
        'source_width': source_width,
        'source_height': source_height,
        'target_width': target_width,
        'ref_height': ref_height,
        'scale_x': scale_x,
        'scale_y': scale_y,
        'new_width': new_glyph.xMax - new_glyph.xMin,
        'new_height': new_glyph.yMax - new_glyph.yMin
    }

# Process each font pair
for i, pair in enumerate(font_pairs, 1):
    weight = pair['weight']
    italic = pair['italic']
    style_suffix = "It" if italic else ""
    variant_name = f"{weight}{style_suffix}"

    print(f"\n[{i}/{len(font_pairs)}] Processing {variant_name}...")
    print("-"*70)

    # Load fonts
    print(f"  Loading Inter-{variant_name}.ttf...")
    inter_font = TTFont(pair['inter'])

    print(f"  Loading SourceSans3-{variant_name}.ttf...")
    ss3_font = TTFont(pair['source_sans'])

    # Copy 'g' from Source Sans 3 to Inter
    print(f"  Copying 'g' from Source Sans 3...")

    stats = copy_and_scale_glyph(
        target_font=inter_font,
        source_font=ss3_font,
        source_glyph_name='g',
        target_glyph_name='g',
        reference_glyph_name='g'  # Use 'g' itself to preserve descender depth
    )

    print(f"    Source dimensions: {stats['source_width']:.0f} × {stats['source_height']:.0f}")
    print(f"    Target dimensions: {stats['target_width']:.0f} × {stats['ref_height']:.0f}")
    print(f"    Scale factors: X={stats['scale_x']:.3f}, Y={stats['scale_y']:.3f}")
    print(f"    Result dimensions: {stats['new_width']:.0f} × {stats['new_height']:.0f}")

    # Save output
    output_path = f"fonts/fonts/Lab3Sans-{variant_name}.ttf"
    print(f"  Saving {output_path}...")
    inter_font.save(output_path)

    # Clean up
    inter_font.close()
    ss3_font.close()

    print(f"  ✓ Complete")

print("\n" + "="*70)
print("Font Generation Complete!")
print("="*70)
print(f"\nGenerated {len(font_pairs)} Lab3 Sans font variants")
print(f"Output directory: fonts/fonts/")
print(f"\nNext steps:")
print(f"  1. Generate web fonts (WOFF2, WOFF)")
print(f"  2. Add Lab3 Sans to font-tester.html")
print(f"  3. Test in browser")
