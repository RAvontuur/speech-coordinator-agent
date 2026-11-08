import re


def assign_annotation_bookmarks(annotation_document, plan_name):
    """Persist stable, unique sequence numbers and readable anchors on annotations."""
    annotations = annotation_document.setdefault("annotations", [])
    assigned = set()

    # Keep every valid, unique assignment regardless of current annotation order.
    for annotation in annotations:
        number = annotation.get("annotation_number")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            anchor = annotation.get("anchor")
            match = re.fullmatch(r".+-(\d+)", anchor) if isinstance(anchor, str) else None
            number = int(match.group(1)) if match else None
        if number is not None and number not in assigned:
            annotation["annotation_number"] = number
            assigned.add(number)
        else:
            annotation.pop("annotation_number", None)

    next_number = max(assigned, default=0) + 1
    for annotation in annotations:
        if "annotation_number" not in annotation:
            while next_number in assigned:
                next_number += 1
            annotation["annotation_number"] = next_number
            assigned.add(next_number)
            next_number += 1
        annotation["anchor"] = f"{plan_name}-{annotation['annotation_number']}"

    annotation_document["plan_name"] = plan_name
    return annotation_document
