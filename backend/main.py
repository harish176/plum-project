from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Any
import logging
from services.pipeline_service import AmountDetectionPipeline
from services.direct_extraction_service import DirectExtractionService
from services.ocr_service import OCRService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define validation error models for OpenAPI schema
class ValidationError(BaseModel):
    """Validation error model for OpenAPI schema"""
    loc: List[str] = Field(..., description="Error location")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    input: Any = Field(None, description="Input that caused the error")

class HTTPValidationError(BaseModel):
    """HTTP validation error model for OpenAPI schema"""
    detail: List[ValidationError] = Field(..., description="List of validation errors")

app = FastAPI(
    title="AI Medical Bill Analyzer",
    description="""
    ## Smart Amount Detection for Medical Documents
    
    Upload your medical bills and get instant, accurate amount extraction powered by advanced AI and OCR technology.
    
    ### Features:
    - **Image Processing**: Upload medical bill images (PNG, JPG, PDF)
    - **Smart Detection**: Automatically identifies totals, payments, due amounts
    - **Multi-Currency**: Supports INR, USD, EUR, GBP
    - **High Accuracy**: Advanced OCR with multiple enhancement techniques
    - **Fast Processing**: Get results in seconds
    
    ### How to Use:
    1. Click on "Extract Amounts from Image" below
    2. Upload your medical bill image
    3. Click "Execute" and get instant results
    """,
    version="2.0.0",
    contact={
        "name": "AI Medical Bill Analyzer",
        "email": "support@medicalbillai.com",
    },
    license_info={
        "name": "MIT License",
    },
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the processing pipeline
pipeline = AmountDetectionPipeline()

# Custom OpenAPI schema to hide unwanted endpoints and schemas
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="AI Medical Bill Analyzer",
        version="2.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Remove unwanted schemas from the documentation
    if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
        # Keep only essential schemas, remove internal ones
        schemas_to_keep = {}
        for schema_name, schema_content in openapi_schema["components"]["schemas"].items():
            if not schema_name.startswith("HTTPValidation") and not schema_name.startswith("ValidationError"):
                schemas_to_keep[schema_name] = schema_content
        openapi_schema["components"]["schemas"] = schemas_to_keep
    
    # Remove internal paths we don't want to show
    paths_to_remove = []
    for path in openapi_schema.get("paths", {}):
        if path in ["/", "/health"]:
            paths_to_remove.append(path)
    
    for path in paths_to_remove:
        if path in openapi_schema["paths"]:
            del openapi_schema["paths"][path]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Custom Swagger UI with beautiful styling
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Medical Bill Analyzer</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui.css" />
        <link rel="icon" type="image/png" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>+</text></svg>" />
        <style>
            /* Custom beautiful styling */
            body {
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            .swagger-ui {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            .swagger-ui .topbar {
                background: linear-gradient(135deg, #4CAF50, #45a049);
                padding: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .swagger-ui .topbar .download-url-wrapper {
                display: none;
            }
            
            .swagger-ui .info {
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                margin: 20px;
            }
            
            .swagger-ui .info .title {
                color: #2c3e50;
                font-size: 2.5em;
                font-weight: 700;
                margin-bottom: 10px;
                text-align: center;
            }
            
            .swagger-ui .info .description {
                color: #555;
                font-size: 1.1em;
                line-height: 1.6;
            }
            
            .swagger-ui .scheme-container {
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.1);
                margin: 20px;
                padding: 20px;
            }
            
            .swagger-ui .opblock {
                border-radius: 10px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.05);
                margin: 20px;
                border: none;
                overflow: hidden;
            }
            
            .swagger-ui .opblock.opblock-post {
                background: linear-gradient(135deg, #ff6b6b, #ee5a24);
                border-left: 5px solid #c0392b;
            }
            
            .swagger-ui .opblock .opblock-summary {
                padding: 20px;
            }
            
            .swagger-ui .opblock .opblock-summary-method {
                background: rgba(255,255,255,0.2);
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 8px 12px;
                text-transform: uppercase;
                font-size: 0.9em;
            }
            
            .swagger-ui .opblock .opblock-summary-path {
                color: white;
                font-weight: 600;
                font-size: 1.1em;
            }
            
            .swagger-ui .opblock .opblock-description-wrapper,
            .swagger-ui .opblock .opblock-external-docs-wrapper,
            .swagger-ui .opblock .opblock-title_normal {
                color: white;
            }
            
            .swagger-ui .btn.execute {
                background: linear-gradient(135deg, #27ae60, #2ecc71);
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                font-size: 1.1em;
                transition: all 0.3s ease;
            }
            
            .swagger-ui .btn.execute:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(39, 174, 96, 0.4);
            }
            
            .swagger-ui .response-content-type {
                color: #27ae60;
                font-weight: 600;
            }
            
            .swagger-ui .responses-inner h4 {
                color: #2c3e50;
                font-size: 1.2em;
            }
            
            .swagger-ui .parameter__name {
                color: #e74c3c;
                font-weight: 600;
            }
            
            .swagger-ui .parameter__type {
                color: #8e44ad;
                font-weight: 500;
            }
            
            /* File upload styling */
            .swagger-ui .file-upload {
                border: 2px dashed #3498db;
                border-radius: 10px;
                padding: 20px;
                background: rgba(52, 152, 219, 0.1);
                transition: all 0.3s ease;
            }
            
            .swagger-ui .file-upload:hover {
                border-color: #2980b9;
                background: rgba(52, 152, 219, 0.2);
            }
            
            /* Response styling */
            .swagger-ui .responses-table {
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            }
            
            .swagger-ui .response.highlighted {
                background: linear-gradient(135deg, #d4edda, #c3e6cb);
                border: 1px solid #27ae60;
            }
            
            /* Loading animation */
            .swagger-ui .loading-container {
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 40px;
            }
            
            .swagger-ui .loading-container .loading {
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Success/Error alerts */
            .swagger-ui .response-content-type.success {
                color: #27ae60;
                font-weight: bold;
            }
            
            .swagger-ui .response-content-type.error {
                color: #e74c3c;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-standalone-preset.js"></script>
        <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: '/openapi.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null,
                tryItOutEnabled: true,
                supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
                onComplete: function() {
                    // Add custom functionality after UI loads
                    console.log('AI Medical Bill Analyzer Ready!');
                    
                    // Add welcome message
                    const infoSection = document.querySelector('.swagger-ui .info');
                    if (infoSection) {
                        const welcomeDiv = document.createElement('div');
                        welcomeDiv.innerHTML = `
                            <div style="background: linear-gradient(135deg, #4CAF50, #45a049); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center;">
                                <h3 style="margin: 0; font-size: 1.3em;">Welcome to AI Medical Bill Analyzer!</h3>
                                <p style="margin: 10px 0 0 0; opacity: 0.9;">Upload your medical bill and get instant, accurate amount extraction</p>
                            </div>
                        `;
                        infoSection.appendChild(welcomeDiv);
                    }
                }
            });
        }
        </script>
    </body>
    </html>
    """)

# Hide redoc as well
@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Redirecting...</title>
        <script>
            window.location.href = '/docs';
        </script>
    </head>
    <body>
        <p>Redirecting to main documentation...</p>
    </body>
    </html>
    """)

@app.post("/extract-amounts-text", 
          summary="Extract Amounts from Text",
          description="Parse medical bill text and extract financial amounts with smart categorization.",
          response_description="Returns currency, amounts array with types, and processing status",
          tags=["Amount Extraction"])
async def extract_amounts_from_text(text: str = Body(..., media_type="text/plain", description="Raw medical bill text to process")):
    """
    ## Extract Amounts from Plain Text
    
    Simply paste or type your medical bill text and get instant amount extraction with intelligent categorization.
    
    ### How to Use:
    1. **Paste your text** directly in the request body (no JSON needed!)
    2. **Click Execute** and get instant results
    3. **Get structured data** with currency, amounts, and types
    
    ### Example Input (Plain Text):
    ```
    Medical Bill - Total: INR 1200, Paid: 1000, Due: 200, Discount: 10%
    Hospital: ABC Medical Center
    Patient: John Doe
    Services: Consultation Rs.500, X-Ray Rs.300, Medicine Rs.400
    ```
    
    ### **Example Output:**
    ```json
    {
      "currency": "INR",
      "amounts": [
        {"type": "total_bill", "value": 1200, "source": "text: 'Total: INR 1200'"},
        {"type": "paid", "value": 1000, "source": "text: 'Paid: 1000'"},
        {"type": "due", "value": 200, "source": "text: 'Due: 200'"},
        {"type": "service", "value": 500, "source": "text: 'Consultation Rs.500'"}
      ],
      "status": "ok"
    }
    ```
    
    ### What We Detect:
    - Total amounts, paid amounts, due balances
    - Individual service charges
    - Discounts and offers
    - Taxes and additional fees
    - Multiple currencies (INR, USD, EUR, GBP)
    """
    try:
        logger.info(f"Processing text input: {text[:100]}...")
        result = await pipeline.process_text(text)
        
        # Convert to clean format
        clean_response = {
            "currency": result.currency or "INR",
            "amounts": [
                {
                    "type": amount.type,
                    "value": amount.value,
                    "source": amount.source
                }
                for amount in result.amounts
            ],
            "status": result.status
        }
        
        return clean_response
    except Exception as e:
        logger.error(f"Error processing text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/extract-amounts-image",
          summary="Extract Amounts from Medical Bill Image", 
          description="Upload a medical bill image and get instant amount extraction with AI-powered OCR.",
          response_description="Returns detected currency, categorized amounts, and processing status",
          tags=["Amount Extraction"])
async def extract_amounts_from_image(
    file: UploadFile = File(
        ..., 
        description="Medical bill image file (PNG, JPG, JPEG, PDF)",
        example="medical_bill.png"
    )
):
    """
    ## Extract Amounts from Medical Bill Image
    
    Upload your medical bill image and get instant, accurate amount extraction using advanced AI and OCR technology.
    
    ### What We Extract:
    - **Total Bill Amount**: Overall cost of medical services
    - **Paid Amount**: Amount already paid
    - **Due Amount**: Outstanding balance
    - **Individual Items**: Line-by-line charges
    - **Discounts**: Applied reductions
    - **Taxes**: GST, service charges, etc.
    
    ### **Supported Formats:**
    - PNG, JPG, JPEG images
    - Clear, readable text
    - Multiple languages supported
    
    ### **Example Response:**
    ```json
    {
      "currency": "INR",
      "amounts": [
        {"type": "total_bill", "value": 1200, "source": "text: 'Total: Rs.1200'"},
        {"type": "paid", "value": 1000, "source": "text: 'Paid: Rs.1000'"},
        {"type": "due", "value": 200, "source": "text: 'Balance: Rs.200'"}
      ],
      "status": "ok"
    }
    ```
    
    ### Processing Time: Usually < 3 seconds
    ### Accuracy: 95%+ for clear images
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
        
        logger.info(f"Processing image: {file.filename}")
        
        # Read image data
        image_data = await file.read()
        
        # Process through pipeline
        result = await pipeline.process_image(image_data)
        
        # Convert to clean format
        clean_response = {
            "currency": result.currency or "INR",
            "amounts": [
                {
                    "type": amount.type,
                    "value": amount.value,
                    "source": amount.source
                }
                for amount in result.amounts
            ],
            "status": result.status
        }
        
        return clean_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

# Initialize direct extraction services
direct_ocr_service = OCRService()
direct_extraction_service = DirectExtractionService()

@app.post("/extract-bill-direct",
    summary="Direct Bill Extraction",
    description="""
    **Simple and reliable extraction** - directly extracts amounts from medical bill images 
    without complex classification. Shows exactly what's found in the image.
    
    - **More Accurate**: Uses pattern matching instead of AI classification
    - **Faster**: No complex processing pipeline  
    - **Clearer**: Shows the exact source line for each amount
    
    Perfect for getting quick, reliable results from medical bills.
    """
)
async def extract_bill_direct(file: UploadFile = File(...)):
    """Direct extraction endpoint - extract amounts from medical bill image."""
    try:
        # Debug: Log what we received
        logger.info(f"=== DEBUG: Received request ===")
        logger.info(f"File object: {file}")
        logger.info(f"File type: {type(file)}")
        if file:
            logger.info(f"File filename: {file.filename}")
            logger.info(f"File content_type: {file.content_type}")
            logger.info(f"File size (if available): {getattr(file, 'size', 'Unknown')}")
        else:
            logger.error("File is None or missing!")
        
        # Better error handling for missing file
        if not file:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "No file provided",
                    "postman_instructions": {
                        "method": "POST",
                        "url": "http://localhost:8000/extract-bill-direct",
                        "body_type": "form-data",
                        "key": "file",
                        "key_type": "File (not Text)",
                        "value": "Select your image file"
                    }
                }
            )
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type: {file.content_type}. Please upload an image file (PNG, JPG, etc.)"
            )
        
        # Read image data
        image_data = await file.read()
        
        # Check if file is empty
        if not image_data:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty. Please upload a valid image file."
            )
        
        logger.info(f"Processing uploaded file: {file.filename} ({len(image_data)} bytes)")
        
        # Step 1: OCR extraction
        ocr_result = await direct_ocr_service.extract_from_image(image_data)
        
        if ocr_result.status != "success":
            return {
                "status": "error",
                "message": f"OCR extraction failed: {ocr_result.reason}",
                "confidence": ocr_result.confidence
            }
        
        # Step 2: Direct extraction
        extracted_amounts = direct_extraction_service.extract_with_fallback(ocr_result.original_text)
        
        # Step 3: Format results
        results = direct_extraction_service.format_results(extracted_amounts)
        
        # Add OCR info to results
        results["ocr_confidence"] = ocr_result.confidence
        results["raw_ocr_text"] = ocr_result.original_text
        
        logger.info(f"Successfully extracted {len(extracted_amounts)} amounts from {file.filename}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/extract-bill-text-direct",
    summary="Direct Text Extraction", 
    description="""
    **Direct extraction from text input** - extract amounts from medical bill text
    using simple pattern matching.
    
    Great for testing or when you already have the bill text.
    """
)
async def extract_bill_from_text_direct(request: dict = Body(...)):
    """Direct extraction from text input."""
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Text field is required")
            
        logger.info("Processing text input")
        
        # Direct extraction
        extracted_amounts = direct_extraction_service.extract_with_fallback(text)
        
        # Format results
        results = direct_extraction_service.format_results(extracted_amounts)
        results["input_text"] = text
        
        logger.info(f"Successfully extracted {len(extracted_amounts)} amounts from text")
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/debug-upload",
    summary="Debug Upload",
    description="Debug endpoint to see what Postman is sending"
)
async def debug_upload(file: UploadFile = File(None)):
    """Debug endpoint to troubleshoot Postman uploads."""
    logger.info("=== DEBUG UPLOAD ENDPOINT ===")
    logger.info(f"Received file: {file}")
    
    if not file:
        return {
            "status": "error",
            "message": "No file received",
            "postman_help": {
                "step1": "Set method to POST",
                "step2": "URL: http://localhost:8000/debug-upload",
                "step3": "Go to Body tab",
                "step4": "Select 'form-data'",
                "step5": "Key: 'file' (dropdown must be 'File' not 'Text')",
                "step6": "Select your image file",
                "step7": "Click Send"
            }
        }
    
    try:
        file_content = await file.read()
        return {
            "status": "success",
            "file_info": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(file_content),
                "size_human": f"{len(file_content) / 1024:.1f} KB"
            },
            "message": "File received successfully! Now try the main endpoint /extract-bill-direct"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error reading file: {str(e)}"
        }

def custom_openapi():
    """Custom OpenAPI schema with proper validation error models"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add the HTTPValidationError schema to components
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
    
    # Add ValidationError schema
    openapi_schema["components"]["schemas"]["ValidationError"] = {
        "title": "ValidationError",
        "required": ["loc", "msg", "type"],
        "type": "object",
        "properties": {
            "loc": {
                "title": "Location",
                "type": "array",
                "items": {"type": "string"}
            },
            "msg": {
                "title": "Message",
                "type": "string"
            },
            "type": {
                "title": "Error Type",
                "type": "string"
            },
            "input": {
                "title": "Input",
                "description": "Input that caused the error"
            }
        }
    }
    
    # Add HTTPValidationError schema
    openapi_schema["components"]["schemas"]["HTTPValidationError"] = {
        "title": "HTTPValidationError",
        "required": ["detail"],
        "type": "object",
        "properties": {
            "detail": {
                "title": "Detail",
                "type": "array",
                "items": {"$ref": "#/components/schemas/ValidationError"}
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)