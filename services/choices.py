from django.db import models


class RequirementFieldType(models.TextChoices):
    TEXT = "text", "Text"
    TEXTAREA = "textarea", "Textarea"
    NUMBER = "number", "Number"
    SELECT = "select", "Select"
    RADIO = "radio", "Radio"
    CHECKBOX = "checkbox", "Checkbox"
    BOOLEAN = "boolean", "Boolean"
    DATE = "date", "Date"