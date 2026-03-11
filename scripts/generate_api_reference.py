import json
import os

def generate_markdown(openapi_path, output_path):
    with open(openapi_path, 'r') as f:
        spec = json.load(f)
        
    md = []
    md.append(f"# {spec['info']['title']} API Reference")
    md.append(f"**Version**: {spec['info']['version']}\n")
    if 'description' in spec['info']:
        md.append(f"{spec['info']['description']}\n")
        
    md.append("## Endpoints\n")
    
    paths = spec.get('paths', {})
    for path, methods in paths.items():
        for method, details in methods.items():
            # Skip hidden or utility endpoints if necessary, but we'll include all for now.
            summary = details.get('summary', 'No summary provided')
            md.append(f"### {method.upper()} `{path}`")
            md.append(f"**{summary}**\n")
            
            if 'description' in details:
                md.append(f"{details['description']}\n")
                
            parameters = details.get('parameters', [])
            if parameters:
                md.append("#### Parameters\n")
                md.append("| Name | In | Required | Type | Description |")
                md.append("|------|----|----------|------|-------------|")
                for param in parameters:
                    req = "Yes" if param.get('required') else "No"
                    schema = param.get('schema', {})
                    ptype = schema.get('type', 'Unknown')
                    desc = param.get('description', '-')
                    # Clean up lines in description
                    desc = desc.replace('\\n', '<br>')
                    md.append(f"| `{param['name']}` | {param['in']} | {req} | {ptype} | {desc} |")
                md.append("\n")
                
            responses = details.get('responses', {})
            if responses:
                md.append("#### Responses\n")
                md.append("| Code | Description |")
                md.append("|------|-------------|")
                for code, resp in responses.items():
                    desc = resp.get('description', '-')
                    md.append(f"| `{code}` | {desc} |")
                md.append("\n")
                
            md.append("---\n")
            
    with open(output_path, 'w') as f:
        f.write('\n'.join(md))
        
    print(f"✅ Successfully wrote API Reference to {output_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    openapi_file = os.path.join(base_dir, 'docs', 'openapi.json')
    output_file = os.path.join(base_dir, 'docs', 'API_REFERENCE.md')
    generate_markdown(openapi_file, output_file)
