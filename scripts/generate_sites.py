#!/usr/bin/env python3
"""Generate mock websites for web agent testing"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_client import LLMClient
from src.site_specs import SITE_SPECS


def generate_site_html(spec: dict, llm: LLMClient) -> str:
    """Generate complete HTML for a mock site"""
    
    prompt = f"""Generate a complete single-file HTML web application.

Site Name: {spec['name']}
Purpose: {spec['purpose']}

Required Elements:
{json.dumps(spec['elements'], indent=2)}

Validation Rules:
{json.dumps(spec['validations'], indent=2)}

Success State:
{json.dumps(spec['success_state'], indent=2)}

Error Display Configuration:
{json.dumps(spec['error_display'], indent=2)}

REQUIREMENTS:
1. Single HTML file with embedded <style> and <script> tags
2. Every interactive element MUST have:
   - A visible <label> element associated with it, OR
   - An aria-label attribute
3. Use semantic HTML elements (button, input, form, etc.)
4. Error messages must appear in elements with class="error"
5. Success messages must appear in elements with class="success"
6. Form validation happens on submit or button click
7. Clean, minimal CSS with good visual hierarchy
8. No external dependencies (no CDN links)
9. All JavaScript must be vanilla JS (no frameworks)
10. The page must be fully functional without any backend

ACCESSIBILITY REQUIREMENTS (CRITICAL):
- All input elements must have associated labels
- All buttons must have descriptive text content
- Use aria-label for any element that needs additional context
- Error messages should be associated with their fields

Return ONLY the complete HTML content. Do not include markdown code blocks or any explanation."""

    response = llm.generate(prompt, max_tokens=8192)
    
    # Clean up response if it contains markdown
    html = response.strip()
    if html.startswith("```html"):
        html = html[7:]
    if html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]
    
    return html.strip()


def generate_server_script() -> str:
    """Generate the Python server script"""
    
    return '''#!/usr/bin/env python3
"""Simple HTTP server for mock websites"""

import http.server
import socketserver
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def log_message(self, format, *args):
        # Suppress logging for cleaner output
        pass


def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Mock sites server running at http://localhost:{PORT}")
        print(f"Available sites:")
        for name in sorted(os.listdir(DIRECTORY)):
            path = os.path.join(DIRECTORY, name)
            if os.path.isdir(path) and not name.startswith('.'):
                print(f"  - http://localhost:{PORT}/{name}/")
        print(f"\\nPress Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\nServer stopped")


if __name__ == "__main__":
    main()
'''


def main():
    """Generate all mock sites"""
    
    import argparse
    parser = argparse.ArgumentParser(description="Generate mock websites")
    parser.add_argument("--api-key", help="Anthropic API key (uses hardcoded default if not provided)")
    args = parser.parse_args()
    
    output_dir = Path(__file__).parent.parent / "mock_sites"
    output_dir.mkdir(exist_ok=True)
    
    llm = LLMClient(api_key=args.api_key)
    
    for spec in SITE_SPECS:
        print(f"Generating {spec['name']}...")
        
        # Generate HTML
        html = generate_site_html(spec, llm)
        
        # Create site directory
        site_dir = output_dir / spec['name']
        site_dir.mkdir(exist_ok=True)
        
        # Write HTML file
        (site_dir / "index.html").write_text(html)
        
        # Write spec for reference
        (site_dir / "spec.json").write_text(json.dumps(spec, indent=2))
        
        print(f"  ✓ Saved to {site_dir}/index.html")
    
    # Generate server script
    (output_dir / "server.py").write_text(generate_server_script())
    os.chmod(output_dir / "server.py", 0o755)
    
    print(f"\n✓ All sites generated in {output_dir}/")
    print(f"  Run: python {output_dir}/server.py")


if __name__ == "__main__":
    main()

