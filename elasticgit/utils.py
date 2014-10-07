from elasticgit.models import TextField, IntegerField

INTROSPECTION_MAPPINGS = {
    TextField: 'string',
    IntegerField: 'integer',
}


def introspect_properties(model_class):
    return dict([
        (field_name, {
            'type': INTROSPECTION_MAPPINGS[type(field_object)],
        })
        for field_name, field_object in model_class._fields.items()
    ])
