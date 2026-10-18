"""Regenerate/check all NPC data after final map export. No Blender required."""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    args = ['--check'] if '--check' in sys.argv else []
    for name in ('placements.py', 'campus_routes.py', 'area_routes.py'):
        subprocess.run([sys.executable, '-I', str(HERE/name), *args], check=True)
    subprocess.run([sys.executable, '-I', str(HERE.parent/'luatest/check_npc_spots.py')], check=True)


if __name__ == '__main__':
    main()
