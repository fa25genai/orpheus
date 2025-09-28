import json
import logging

from service_slides.impl.llm_chain.slide_structure import DetailedSlideStructure, DetailedSlideStructureItem
from service_slides.impl.manager.layout_manager import LayoutTemplate


_log = logging.getLogger("mocks")

def make_mock_slide_structure() -> DetailedSlideStructure:
    _log.warning("Using mocks for slide structure!")
    mock_items = [
        DetailedSlideStructureItem(
            content="Title: Introduction to For Loops\nHello, and welcome! Today, we're going to dive into the world of 'for loops' in Python. Now, you might be wondering, what *is* a for loop? Simply put, a for loop is a control flow statement that allows us to repeatedly execute a block of code.",
            layout="default",
        ),
        DetailedSlideStructureItem(
            content="Title: Importance of For Loops\nWhy are for loops so important? Well, in programming, we often need to process collections of data "
            "– things like lists, tuples, or even strings. A for loop provides a clean and efficient way to iterate through each item in these collections and perform some operation on it.",
            layout="default",
        ),
        DetailedSlideStructureItem(
            content="Title: Basic Syntax of For Loops\nThe basic syntax in Python is quite straightforward: `for item in iterable:`.  Let's break that down. "
            "'iterable' is anything that can be looped over – a list, a tuple, a string, or something similar. The 'item' is a variable that takes on the value of each element in the iterable, one at a time, during each iteration of the loop.",
            layout="default",
        ),
        DetailedSlideStructureItem(
            content="Title: Example of For Loop\nLet's illustrate with a simple example. Imagine you have a list of names: `names = ['Alice', 'Bob', 'Charlie']`. "
            "A for loop would allow you to print each name in the list without having to write separate print statements for each one.  The code would look like this: `for name in names: print(name)`.",
            layout="default",
        ),
        DetailedSlideStructureItem(
            content="Title: Nesting For Loops\nNow, let's talk about nesting. You can actually put a for loop *inside* another for loop. "
            "This is useful when you need to process data that has multiple dimensions, like a grid or a matrix. For example, you might have a list of lists, and you’d use a nested for loop to access each element in the inner lists.",
            layout="default",
        ),
    ]

    return DetailedSlideStructure(items=mock_items)


def make_mock_slide_content(
    text: str,
    layout_template: LayoutTemplate,
) -> str:
    _log.warning("Using mocks for slide content!")
    template_vars = {}
    for field_name in layout_template.schema.keys():
        if "headline" in field_name.lower():
            first_line = text.split("\n", 1)[0]
            template_vars[field_name] = first_line.replace("Title: ", "")
        else:
            body = text.split("\n", 1)[1] if "\n" in text else ""
            template_vars[field_name] = body

    try:
        final_slide = layout_template.template.substitute(**template_vars)
    except KeyError:
        final_slide = layout_template.template.safe_substitute(**template_vars)

    return str(final_slide)
