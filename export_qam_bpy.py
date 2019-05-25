import bpy
import sys
import os
import glob
import argparse

class ArgumentParserForBlender(argparse.ArgumentParser):
    def _get_argv_after_doubledash(self):
        try:
            idx = sys.argv.index("--")
            return sys.argv[idx+1:] # the list after '--'
        except ValueError as e: # '--' not in the list:
            return []

    def parse_args(self):
        return super().parse_args(args=self._get_argv_after_doubledash())

class ArgumentParserWrapper:
    def __init__(self, parser):
        self.parser = parser
        self.dict = {}

    def add_fake_argument(self, name, type):
        if type is bool:
            self.parser.add_argument('--' + name, default=argparse.SUPPRESS, action='store_true')
        else:
            self.parser.add_argument('-' + name, default=argparse.SUPPRESS, type=type)

        self.dict[name] = lambda x: getattr(x, name) if hasattr(x, name) else None

    def parse_args(self):
        args = self.parser.parse_args()
        kwargs = { k : v(args) for k, v in self.dict.items()}
        kwargs = { k : v for k, v in kwargs.items() if v is not None}
        return args, kwargs

wrapper = ArgumentParserWrapper(ArgumentParserForBlender(description="Export '.blend' to '.qam' models"))
wrapper.parser.add_argument('-input', required=True, nargs='+')
wrapper.add_fake_argument('text_output', bool)
wrapper.add_fake_argument('use_selection', bool)
wrapper.add_fake_argument('use_mesh_modifiers', bool)
wrapper.add_fake_argument('include_uvs', bool)
wrapper.add_fake_argument('include_tangent_binormal', bool)
wrapper.add_fake_argument('include_bones', bool)
wrapper.add_fake_argument('include_armature', bool)
wrapper.add_fake_argument('include_animations', bool)
wrapper.add_fake_argument('bones_per_vert_mod', int)
wrapper.add_fake_argument('bones_per_vert_max', int)
wrapper.add_fake_argument('bones_per_mesh_max', int)
wrapper.add_fake_argument('approx_animations', bool)
wrapper.add_fake_argument('debug_animations', bool)
wrapper.add_fake_argument('approx_err_translations', float)
wrapper.add_fake_argument('approx_err_rotations', float)
wrapper.add_fake_argument('approx_err_scales', float)
wrapper.add_fake_argument('filter_partial_animations', bool)
args, kwargs = wrapper.parse_args()

files = []
for path in args.input:
    path = os.path.abspath(path)
    if os.path.isdir(path):
        files += [f for f in glob.glob(path + "/**/*.blend", recursive=True)]
    elif path.endswith('.blend'):
        files.append(os.path.abspath(path))

for input in files:
    bpy.ops.wm.open_mainfile(filepath=input)

    output = os.path.splitext(input)[0] + ".qam"
    bpy.ops.export_scene.qam(filepath=output, **kwargs)