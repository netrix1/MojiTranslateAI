export interface BBox {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
}

export interface Region {
    region_id: string;
    bbox: [number, number, number, number]; // x1, y1, x2, y2
    polygon?: number[][]; // [[x,y], [x,y], ...]
    type_hint: string;
    score?: number;
    text?: string; // OCR raw text if available
}

export interface PageData {
    page_number: number;
    image_file: string;
    regions: Region[];
    notes?: string;
}

export interface RegionFile {
    chapter_id: string;
    pages: PageData[];
}

export interface Job {
    job_id: string;
    status: string;
    created_on: string;
    context: any;
}

export interface RenderingStyle {
    font_family?: string;
    text_color?: string; // hex
    stroke_color?: string; // hex
    stroke_width?: number;
    is_bold?: boolean;
    is_italic?: boolean;
    alignment?: string; // 'left' | 'center' | 'right'
    font_size?: number; // scale 1-10 relative to image width
    angle?: number; // degrees -180 to 180
    box_scale?: number; // scale factor 0.5 to 2.0
    line_spacing?: number; // line-height multiplier (e.g. 1.0, 1.2, 1.5)
}

export interface OCRBlock {
    block_id?: string; // Often present from backend
    text?: string;
    original_text?: string;
    translation?: string; // Added this implicit field often used
    confidence?: number;
    bbox?: [number, number, number, number];
    polygon?: number[][]; // Polygon support in Blocks too
    group_id?: string;
    reading_order?: number;
    region_id?: string; // linkage to region
    rendering_style?: RenderingStyle;
}

export interface OCRPage {
    page_number: number;
    blocks: OCRBlock[];
}

export interface OCRFile {
    pages: OCRPage[];
}
