"""
Quick analysis script to check if .exe is Python-based and extract information
"""
import os
import sys

def check_pyinstaller(exe_path):
    """Check if .exe is created with PyInstaller"""
    try:
        with open(exe_path, 'rb') as f:
            header = f.read(100)
            # PyInstaller markers
            if b'MEI' in header or b'PYINSTALLER' in header.upper():
                return True
            # Check for Python DLL references
            f.seek(0)
            content = f.read(10000)
            if b'python' in content.lower() or b'pyinstaller' in content.lower():
                return True
    except Exception as e:
        print(f"Error reading file: {e}")
    return False

def extract_strings(exe_path, min_length=4):
    """Extract readable strings from binary"""
    strings = set()
    try:
        with open(exe_path, 'rb') as f:
            current_string = b''
            while True:
                byte = f.read(1)
                if not byte:
                    break
                
                # Check if printable ASCII
                if 32 <= byte[0] <= 126:  # Printable ASCII
                    current_string += byte
                else:
                    if len(current_string) >= min_length:
                        try:
                            s = current_string.decode('ascii', errors='ignore')
                            if s.strip():
                                strings.add(s.strip())
                        except:
                            pass
                    current_string = b''
    except Exception as e:
        print(f"Error extracting strings: {e}")
    
    return sorted(strings)

def analyze_exe(exe_path):
    """Analyze .exe file"""
    if not os.path.exists(exe_path):
        print(f"File not found: {exe_path}")
        return
    
    print(f"\n{'='*60}")
    print(f"Analyzing: {exe_path}")
    print(f"{'='*60}\n")
    
    # File info
    size = os.path.getsize(exe_path)
    print(f"File Size: {size:,} bytes ({size/1024/1024:.2f} MB)")
    
    # Check if PyInstaller
    is_pyinstaller = check_pyinstaller(exe_path)
    print(f"PyInstaller: {'YES ✅ (Can be decompiled!)' if is_pyinstaller else 'NO ❌ (Compiled language)'}")
    
    # Extract strings
    print("\nExtracting strings (this may take a moment)...")
    strings = extract_strings(exe_path, min_length=6)
    
    # Filter relevant strings
    vpn_keywords = ['expressvpn', 'pia', 'vpn', 'connect', 'disconnect', 'server', 'location']
    relevant_strings = []
    
    for s in strings:
        s_lower = s.lower()
        if any(keyword in s_lower for keyword in vpn_keywords):
            relevant_strings.append(s)
    
    print(f"\nTotal strings found: {len(strings)}")
    print(f"VPN-related strings: {len(relevant_strings)}")
    
    if relevant_strings:
        print("\n🔍 VPN-Related Strings Found:")
        print("-" * 60)
        for s in relevant_strings[:50]:  # Show first 50
            print(f"  • {s}")
        if len(relevant_strings) > 50:
            print(f"\n  ... and {len(relevant_strings) - 50} more")
    
    # Check for file paths
    file_paths = [s for s in strings if ('\\' in s or '/' in s) and len(s) > 10]
    if file_paths:
        print("\n📁 File Paths Found:")
        print("-" * 60)
        for path in file_paths[:20]:
            print(f"  • {path}")
    
    # Check for CLI commands
    cli_commands = [s for s in strings if any(cmd in s.lower() for cmd in ['connect', 'disconnect', 'status', 'list'])]
    if cli_commands:
        print("\n⚙️  Possible CLI Commands:")
        print("-" * 60)
        for cmd in cli_commands[:20]:
            print(f"  • {cmd}")
    
    print(f"\n{'='*60}")
    print("Analysis Complete!")
    print(f"{'='*60}\n")
    
    # Save to file
    output_file = "exe_analysis.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Analysis of: {exe_path}\n")
        f.write(f"Size: {size:,} bytes\n")
        f.write(f"PyInstaller: {is_pyinstaller}\n\n")
        f.write("VPN-Related Strings:\n")
        f.write("-" * 60 + "\n")
        for s in relevant_strings:
            f.write(f"{s}\n")
        f.write("\n\nAll Strings (sample):\n")
        f.write("-" * 60 + "\n")
        for s in strings[:200]:
            f.write(f"{s}\n")
    
    print(f"📄 Full analysis saved to: {output_file}")

if __name__ == "__main__":
    exe_path = r"Bot Inspried from\run.exe"
    
    if len(sys.argv) > 1:
        exe_path = sys.argv[1]
    
    analyze_exe(exe_path)








