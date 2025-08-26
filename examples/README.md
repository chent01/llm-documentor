# Medical Software Analysis Tool Example Files

## Example Configuration

This directory contains example files for the Medical Software Analysis Tool, including sample configuration files.

### example_config.json

This file provides a comprehensive example of the configuration options available for the Medical Software Analysis Tool with comments explaining each option. It includes settings for:

- LLM backend configuration (OpenAI, Anthropic, local models, or mock backend)
- Database settings
- Export preferences
- UI customization
- Analysis parameters
- Logging options
- Custom application settings

### LLM Backend Configuration Examples

We provide several example configuration files for different LLM backend setups:

#### clean_config.json

A clean version of the example configuration file without comments, ready to be used as a starting point for your own configuration.

#### local_lan_config.json

Configuration for connecting to a local LLM server on your LAN. This setup uses:
- `backend_type`: "local"
- `server_url`: URL to your LAN-hosted LLM server
- `api_key`: API key if required by your local server
- `model_name`: Name of the model on your local server

#### local_machine_config.json

Configuration for running a local LLM directly on your machine. This setup uses:
- `backend_type`: "local"
- `model_path`: Path to your local model file (typically .gguf format)
- `batch_size`: Processing batch size for local inference
- `context_window`: Context window size in tokens

#### openai_config.json

Configuration for using OpenAI's API. This setup uses:
- `backend_type`: "openai"
- `api_key`: Your OpenAI API key
- `model_name`: OpenAI model to use (e.g., "gpt-4")
- `embedding_model`: Model for embeddings

#### mock_config.json

Configuration for using the mock backend for testing purposes. This setup uses:
- `backend_type`: "mock"

This configuration is useful for testing the application without connecting to actual LLM services.

## How to Use

1. Copy the example configuration to your preferred location:
   ```bash
   cp examples/example_config.json my_config.json
   ```

2. Edit the configuration file to match your requirements:
   ```bash
   # Edit with your preferred text editor
   nano my_config.json
   ```

3. **Important**: Remove all comments from the JSON file as they are not officially supported in the JSON format. The comments in the example file are for documentation purposes only.

4. Run the application with your custom configuration:
   ```bash
   medical-analyzer --config my_config.json
   ```

## Documentation

For detailed documentation on all configuration options, please refer to the [Configuration Guide](../docs/CONFIG.md) in the docs directory.

## Support

For additional support, please contact: info@tcgindustrial.com.au