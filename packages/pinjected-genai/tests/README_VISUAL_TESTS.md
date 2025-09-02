# Visual Verification Tests

These tests generate actual images using Vertex AI's Imagen API and display them using matplotlib for manual verification.

## Running Visual Tests

### Run a single test:
```bash
uv run pytest tests/test_visual_verification.py::test_visual_single_image -xvs
```

### Run all visual tests:
```bash
uv run pytest tests/test_visual_verification.py -xvs
```

## Available Tests

1. **test_visual_single_image** - Generate a single image with a specific prompt
2. **test_visual_multiple_images** - Generate 4 images in a grid layout
3. **test_visual_different_prompts** - Compare images from different prompts
4. **test_visual_image_with_story** - Generate image with accompanying story text
5. **test_visual_describe_generated_image** - Generate an image and then describe it
6. **test_visual_aspect_ratios** - Test different composition types

## Output

Each test will:
1. Generate images using the Imagen API
2. Save a visualization to a temporary PNG file (path shown in logs)
3. Display the matplotlib plot (if running with display available)

The temporary files are saved in your system's temp directory and the paths are printed in the test output for inspection.

## Note

These tests require:
- Valid GCP credentials configured
- Access to Vertex AI Imagen API
- matplotlib installed (included in dev dependencies)