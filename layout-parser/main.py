import cv2
from PIL import Image

# Pillow >=10 removes the Image.LINEAR alias that detectron2 expects.
if not hasattr(Image, "LINEAR"):
    linear = getattr(Image, "BILINEAR", None)
    if linear is None:
        resampling = getattr(Image, "Resampling", None)
        if resampling is not None:
            linear = getattr(resampling, "BILINEAR", None)
    if linear is not None:
        Image.LINEAR = linear  # type: ignore[attr-defined]


def main() -> None:
    import layoutparser as lp

    image = cv2.imread("example-slide.png")
    image = image[..., ::-1]

    model = lp.Detectron2LayoutModel(
        "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config",
        extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.8],
        label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
    )
    # Load the deep layout model from the layoutparser API
    # For all the supported model, please check the Model Zoo page:
    # https://layout-parser.readthedocs.io/en/latest/notes/modelzoo.html

    layout = model.detect(image)
    annotated_image = lp.draw_box(image, layout, box_width=3)
    annotated_path = "example-slide-annotated.png"
    annotated_image.save(annotated_path)
    print(f"Saved annotated layout to {annotated_path}")

    figure_blocks = [
        block
        for block in layout
        if getattr(block, "type", None) == "Figure" and block.score > 0.9
    ]
    for idx, block in enumerate(figure_blocks, start=1):
        x1, y1, x2, y2 = map(int, block.coordinates)
        x1 = max(x1, 0)
        y1 = max(y1, 0)
        x2 = min(x2, image.shape[1])
        y2 = min(y2, image.shape[0])
        if x2 <= x1 or y2 <= y1:
            continue
        crop = image[y1:y2, x1:x2]
        figure_path = f"figure_{idx:02d}.png"
        Image.fromarray(crop).save(figure_path)
        print(f"Saved figure block {idx} to {figure_path}")

    print(layout)


if __name__ == "__main__":
    main()
