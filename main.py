import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import random
import io
import os
from tqdm import tqdm


def check_file_exists ( file_path, file_type ):
    """Check if a file exists at the given path."""
    if not os.path.exists ( file_path ):
        raise FileNotFoundError ( f"{file_type} file not found: {file_path}" )


def get_image_dimensions ( image_path, max_width=200 ):
    """Get and adjust image dimensions while preserving aspect ratio."""
    img = ImageReader ( image_path )
    img_width, img_height = img.getSize ()
    aspect_ratio = img_width / img_height

    if img_width > max_width:
        img_width = max_width
        img_height = img_width / aspect_ratio

    return img_width, img_height


def determine_page_orientation ( page ):
    """Determine page dimensions and orientation, accounting for rotation."""
    page_width = float ( page.mediabox.width )
    page_height = float ( page.mediabox.height )
    rotation = page.get ( '/Rotate', 0 )

    if rotation in (90, 270):
        page_width, page_height = page_height, page_width

    is_landscape = page_width > page_height
    return page_width, page_height, is_landscape


def calculate_position_bounds ( page_width, page_height, img_width, img_height,
                                top_margin, bottom_margin, side_margin ):
    """Calculate the bounds for random image placement."""
    max_x = page_width - img_width - side_margin
    min_x = side_margin
    max_y = page_height - img_height - top_margin
    min_y = bottom_margin

    if max_x <= min_x or max_y <= min_y:
        raise ValueError ( "Margins too large for image placement with current image size" )

    return min_x, max_x, min_y, max_y


def get_random_position ( min_x, max_x, min_y, max_y ):
    """Generate random position within bounds."""
    x_pos = random.uniform ( min_x, max_x )
    y_pos = random.uniform ( min_y, max_y )
    return x_pos, y_pos


def create_image_layer ( page_width, page_height, img, img_width, img_height,
                         x_pos, y_pos, rotation_angle ):
    """Create a PDF layer with the rotated image."""
    packet = io.BytesIO ()
    can = canvas.Canvas ( packet, pagesize=(page_width, page_height) )

    can.saveState ()
    can.translate ( x_pos, y_pos )
    can.rotate ( rotation_angle )
    can.drawImage (
        img,
        0, 0,
        width=img_width,
        height=img_height,
        preserveAspectRatio=True,
        mask='auto'
    )
    can.restoreState ()
    can.save ()

    packet.seek ( 0 )
    return PyPDF2.PdfReader ( packet ).pages [ 0 ]


def process_page ( page, img, img_width, img_height, top_margin, bottom_margin,
                   side_margin, rotation_angle ):
    """Process a single PDF page by adding the image."""
    page_width, page_height, _ = determine_page_orientation ( page )

    min_x, max_x, min_y, max_y = calculate_position_bounds (
        page_width, page_height, img_width, img_height,
        top_margin, bottom_margin, side_margin
    )

    x_pos, y_pos = get_random_position ( min_x, max_x, min_y, max_y )

    image_page = create_image_layer (
        page_width, page_height, img, img_width, img_height,
        x_pos, y_pos, rotation_angle
    )

    page.merge_page ( image_page )
    return page


def insert_image_to_pdf ( input_pdf_path, image_path, output_pdf_path,
                          top_margin=100, bottom_margin=50, side_margin=50 ):
    """
    Main function to insert image into all PDF pages with random rotation (0-15 degrees).
    Rotation angle is independent of orientation in range but direction adjusts:
    - Portrait: 0 to 15 degrees (clockwise)
    - Landscape: -15 to 0 degrees (counterclockwise)

    Args:
        input_pdf_path (str): Path to input PDF file
        image_path (str): Path to image file
        output_pdf_path (str): Path for output PDF file
        top_margin (float): Margin from top in points
        bottom_margin (float): Margin from bottom in points
        side_margin (float): Margin from sides in points
    """
    check_file_exists ( input_pdf_path, "Input PDF" )
    check_file_exists ( image_path, "Image" )

    input_pdf = PyPDF2.PdfReader ( input_pdf_path )
    output_pdf = PyPDF2.PdfWriter ()
    img_width, img_height = get_image_dimensions ( image_path )
    img = ImageReader ( image_path )

    for page_num in tqdm ( range ( len ( input_pdf.pages ) ), desc="Processing pages" ):
        try:
            page = input_pdf.pages [ page_num ]
            # Determine orientation for rotation direction
            _, _, is_landscape = determine_page_orientation ( page )
            # Generate random rotation angle (0-15 degrees)
            # Portrait: clockwise (0 to 15), Landscape: counterclockwise (90 to 75),
            rotation_angle = random.uniform ( 0, 15 ) if not is_landscape else random.uniform ( 90, 75 )
            processed_page = process_page (
                page, img, img_width, img_height,
                top_margin, bottom_margin, side_margin, rotation_angle
            )
            output_pdf.add_page ( processed_page )
        except ValueError as e:
            raise ValueError ( f"Page {page_num + 1}: {str ( e )}" )

    with open ( output_pdf_path, 'wb' ) as output_file:
        output_pdf.write ( output_file )


# Example usage
if __name__ == "__main__":
    try:
        input_pdf = "inputbw.pdf"
        image_file = "image.png"
        output_pdf = "output_with_image.pdf"

        insert_image_to_pdf (
            input_pdf,
            image_file,
            output_pdf,
            top_margin=150,
            bottom_margin=75,
            side_margin=50
        )
        print ( "PDF processing completed successfully!" )

    except Exception as e:
        print ( f"An error occurred: {str ( e )}" )