import cv2


input_path = "input/receipt.jpeg"
output_path = "output/processed_receipt.jpeg"


image = cv2.imread(input_path)

if image is None:
    raise FileNotFoundError(f"Could not read image: {input_path}")


# 1. Upscale the image
scale = 4

resized = cv2.resize(
    image,
    None,
    fx=scale,
    fy=scale,
    interpolation=cv2.INTER_CUBIC
)


# 2. Convert to grayscale
gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)


# 3. Improve local contrast
clahe = cv2.createCLAHE(
    clipLimit=2.0,
    tileGridSize=(8, 8)
)

enhanced = clahe.apply(gray)


# 4. Light denoising
denoised = cv2.GaussianBlur(
    enhanced,
    (3, 3),
    0
)


# 5. Save the processed image
cv2.imwrite(
    output_path,
    denoised
)


print("Preprocessing completed successfully!")
print(f"Saved to: {output_path}")