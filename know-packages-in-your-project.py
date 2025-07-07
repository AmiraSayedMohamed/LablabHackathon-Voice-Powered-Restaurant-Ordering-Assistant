import pkg_resources
import subprocess
import sys

def get_installed_packages():
    # Get all installed packages
    installed_packages = pkg_resources.working_set
    return sorted(["%s==%s" % (i.key, i.version) for i in installed_packages])

def generate_requirements_file():
    # Get installed packages
    packages = get_installed_packages()
    
    # Write to requirements.txt
    with open('requirements.txt', 'w') as f:
        for package in packages:
            f.write(package + '\n')
    
    print("requirements.txt file has been created successfully!")

if __name__ == "__main__":
    generate_requirements_file()

