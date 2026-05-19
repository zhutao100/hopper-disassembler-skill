<span id="mcp_server"></span>

# MCP Server

Starting with Hopper 6.0, you now have the ability to query any Hopper document using an LLM, like Claude, ChatGPT, Gemini-cli or even a local LLM using ollama, LM Studio...

Hopper provides an MCP server using the STDIO transport protocol. I'll use the Claude desktop application as an example.

Open or create the file ~/Library/Application Support/Claude/claude_desktop_config.json and add the Hopper MSP Server to the list like this:

{ "mcpServers": { "HopperMCPServer": { "command": "/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer", "args": \[\], "env": {} } } }

***<u>Note:</u>*** Some clients have issues with the space character in the path. In order to circumvent the problem, here are a few solutions:

you can use this alternative JSON configuration (works with Cursor):

{ "mcpServers": { "HopperMCPServer": { "command": "/bin/bash", "args": \[ "-c", "/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer" \], "env": {} } } }

or even (works with augment code):

{ "mcpServers": { "HopperMCPServer": { "command": "/Applications/Hopper\\ Disassembler.app/Contents/MacOS/HopperMCPServer", "args": \[\], "env": {} } } }

if none of those JSON configurations works, you can create a symbolic link from the HopperMCPServer binary to another directory, with a command like:

\$ sudo ln -s "/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer" /usr/local/bin/HopperMCPServer

Once done, the JSON becomes:

{ "mcpServers": { "HopperMCPServer": { "command": "/usr/local/bin/HopperMCPServer", "args": \[\], "env": {} } } }
