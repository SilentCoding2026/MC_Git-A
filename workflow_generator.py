import json


with open('config.json', 'r') as json_file:
    replacements = json.load(json_file)


# 1. Define your variables and their new values
replacements = {
    '__SERVER_JAR_NAME__': replacements['server_file_name'],
    '__JAVA_VER__': replacements['java_version'],
    '__JAVA_ARGS__': replacements['server_args']
}

# 2. Read the template file
with open('template.yml', 'r') as file:
    content = file.read()

# 3. Loop and replace every variable automatically
for placeholder, real_value in replacements.items():
    content = content.replace(placeholder, real_value)

# 4. Save the final workflow file
with open('start_server.yml', 'w') as file:
    file.write(content)

print("All 3 variables injected and workflow generated!")