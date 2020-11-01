// Clear Head and Length images

#version 430 core

#extension GL_ARB_compute_shader          : require
#extension GL_ARB_shader_image_load_store : require
#extension GL_EXT_shader_image_load_store : require

layout (local_size_x = 4, local_size_y = 4) in;
layout (binding = 1, r32ui) writeonly restrict uniform uimage2D TexHead;
layout (binding = 2, r32ui) writeonly restrict uniform uimage2D TexLength;

void main()
{
  ivec2 p = ivec2(gl_GlobalInvocationID.xy);

  const uvec4 head0 = uvec4(0xffffffffu);
  imageStore(TexHead, p, head0);

  const uvec4 length0 = uvec4(0u);
  imageStore(TexLength, p, length0);
}
