from typing import List, Dict
from string import Template


class LayoutDescription:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description


class LayoutTemplate:
    def __init__(self, name: str, template: Template, schema: Dict[str, str]):
        self.name = name
        self.template = template
        self.schema = schema


class LayoutManager:
    def __init__(self) -> None:
        self._templates = {
            "default": LayoutTemplate(
                "default",
                Template(
                    """---
layout: default
---

# ${headline}

${content}
"""
                ),
                {
                    "headline": "Title/headline of this slide",
                    "content": "Main content of the slide. Must be in sli.dev markdown syntax",
                },
            ),
            "center": LayoutTemplate(
                "center",
                Template(
                    """---
layout: center
---

# ${headline}

${content}
"""
                ),
                {
                    "headline": "Title centered on the slide",
                    "content": "Main content, centered on the slide",
                },
            ),
            "cover": LayoutTemplate(
                "cover",
                Template(
                    """---
layout: cover
---

# ${title}

${subtitle}
"""
                ),
                {
                    "title": "Main presentation title",
                    "subtitle": "Optional subtitle, author, or contextualization",
                },
            ),
            "end": LayoutTemplate(
                "end",
                Template(
                    """---
layout: end
---

# ${message}
"""
                ),
                {"message": "Closing message for the final slide"},
            ),
            "fact": LayoutTemplate(
                "fact",
                Template(
                    """---
layout: fact
---

# ${fact}
"""
                ),
                {"fact": "A single fact or data point to highlight prominently"},
            ),
            "full": LayoutTemplate(
                "full",
                Template(
                    """---
layout: full
---

${content}
"""
                ),
                {"content": "Full-screen content (text, image, or code)"},
            ),
            "image-left": LayoutTemplate(
                "image-left",
                Template(
                    """---
layout: image-left
image: ${image}
class: ${class_name}
---

${content}
"""
                ),
                {
                    "image": "Path or URL to the image",
                    "class_name": "Optional custom CSS class for the right content",
                    "content": "Text content shown on the right side",
                },
            ),
            "image-right": LayoutTemplate(
                "image-right",
                Template(
                    """---
layout: image-right
image: ${image}
class: ${class_name}
---

${content}
"""
                ),
                {
                    "image": "Path or URL to the image",
                    "class_name": "Optional custom CSS class for the left content",
                    "content": "Text content shown on the left side",
                },
            ),
            "image": LayoutTemplate(
                "image",
                Template(
                    """---
layout: image
image: ${image}
backgroundSize: ${background_size}
---
"""
                ),
                {
                    "image": "Path or URL to the image",
                    "background_size": "Background size (e.g. 'cover', 'contain', or CSS value)",
                },
            ),
            "iframe-left": LayoutTemplate(
                "iframe-left",
                Template(
                    """---
layout: iframe-left
url: ${url}
class: ${class_name}
---

${content}
"""
                ),
                {
                    "url": "Web page to embed",
                    "class_name": "Optional CSS class for the right content",
                    "content": "Text content shown on the right side",
                },
            ),
            "iframe-right": LayoutTemplate(
                "iframe-right",
                Template(
                    """---
layout: iframe-right
url: ${url}
class: ${class_name}
---

${content}
"""
                ),
                {
                    "url": "Web page to embed",
                    "class_name": "Optional CSS class for the left content",
                    "content": "Text content shown on the left side",
                },
            ),
            "iframe": LayoutTemplate(
                "iframe",
                Template(
                    """---
layout: iframe
url: ${url}
---
"""
                ),
                {"url": "Web page to embed as the main content"},
            ),
            "intro": LayoutTemplate(
                "intro",
                Template(
                    """---
layout: intro
---

# ${title}

${description}

_Author: ${author}_
"""
                ),
                {
                    "title": "Presentation title",
                    "description": "Short description",
                    "author": "Author name(s)",
                },
            ),
            "none": LayoutTemplate(
                "none",
                Template(
                    """---
layout: none
---

${content}
"""
                ),
                {"content": "Raw content without styling"},
            ),
            "quote": LayoutTemplate(
                "quote",
                Template(
                    """---
layout: quote
---

> ${quote}

— ${author}
"""
                ),
                {"quote": "Quotation text", "author": "Source or author"},
            ),
            "section": LayoutTemplate(
                "section",
                Template(
                    """---
layout: section
---

# ${section_title}
"""
                ),
                {"section_title": "Section heading"},
            ),
            "statement": LayoutTemplate(
                "statement",
                Template(
                    """---
layout: statement
---

# ${statement}
"""
                ),
                {"statement": "Main affirmation or statement"},
            ),
            "two-cols": LayoutTemplate(
                "two-cols",
                Template(
                    """---
layout: two-cols
---

# ${title_left}

${left}

::right::

# ${title_right}

${right}
"""
                ),
                {
                    "title_left": "Heading for the left column",
                    "left": "Content for the left column",
                    "title_right": "Heading for the right column",
                    "right": "Content for the right column",
                },
            ),
            "two-cols-header": LayoutTemplate(
                "two-cols-header",
                Template(
                    """---
layout: two-cols-header
---

${header}

::left::

# ${title_left}

${left}

::right::

# ${title_right}

${right}
"""
                ),
                {
                    "header": "Header spanning the top",
                    "title_left": "Heading for the left column",
                    "left": "Content for the left column",
                    "title_right": "Heading for the right column",
                    "right": "Content for the right column",
                },
            ),
        }

    async def get_available_layouts(self, courseId: str) -> List[LayoutDescription]:
        return [
            LayoutDescription("center", "Displays the content in the middle of the screen."),
            LayoutDescription(
                "cover",
                "Used to display the cover page for the presentation, may contain the presentation title, contextualization, etc.",
            ),
            LayoutDescription("default", "The most basic layout, to display any kind of content."),
            LayoutDescription("end", "The final page for the presentation."),
            LayoutDescription(
                "fact", "To show some fact or data with a lot of prominence on the screen."
            ),
            LayoutDescription("full", "Use all the space of the screen to display the content."),
            LayoutDescription(
                "image-left",
                "Shows an image on the left side of the screen, the content will be placed on the right side.",
            ),
            LayoutDescription(
                "image-right",
                "Shows an image on the right side of the screen, the content will be placed on the left side.",
            ),
            LayoutDescription("image", "Shows an image as the main content of the page."),
            LayoutDescription(
                "iframe-left",
                "Shows a web page on the left side of the screen, the content will be placed on the right side.",
            ),
            LayoutDescription(
                "iframe-right",
                "Shows a web page on the right side of the screen, the content will be placed on the left side.",
            ),
            LayoutDescription("iframe", "Shows a web page as the main content of the page."),
            LayoutDescription(
                "intro",
                "To introduce the presentation, usually with the presentation title, a short description, the author, etc.",
            ),
            LayoutDescription("none", "A layout without any existing styling."),
            LayoutDescription("quote", "To display a quotation with prominence."),
            LayoutDescription(
                "section", "Used to mark the beginning of a new presentation section."
            ),
            LayoutDescription(
                "statement", "Make an affirmation/statement as the main page content."
            ),
            LayoutDescription("two-cols", "Separates the page content in two columns."),
            LayoutDescription(
                "two-cols-header",
                "Separates the upper and lower lines of the page content, and the second line separates the left and right columns.",
            ),
        ]

    async def get_layout_template(self, courseId: str, layoutName: str) -> LayoutTemplate:
        try:
            return self._templates[layoutName]
        except KeyError:
            raise ValueError(f"Unknown layout: {layoutName}")
