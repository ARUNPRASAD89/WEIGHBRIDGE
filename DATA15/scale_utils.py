def scale_template_fields(template_fields, 
                         original_width_mm, original_height_mm, 
                         target_width_mm, target_height_mm):
    scale_x = target_width_mm / original_width_mm
    scale_y = target_height_mm / original_height_mm
    scaled_fields = []
    for field in template_fields:
        scaled_fields.append({
            'fieldname': field['fieldname'],
            'x': field['x'] * scale_x,
            'y': field['y'] * scale_y,
            'width': field['width'] * scale_x,
            'height': field['height'] * scale_y,
            'fontname': field['fontname'],
            'fontsize': int(field['fontsize'] * min(scale_x, scale_y)),
        })
    return scaled_fields