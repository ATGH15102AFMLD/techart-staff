#version 430 core

#extension GL_ARB_shader_storage_buffer_object : require
#extension GL_ARB_shading_language_packing     : require

out vec4 FragColor;

layout (binding = 1, r32ui) readonly restrict uniform uimage2D ImageHead;
layout (binding = 2, r32ui) readonly restrict uniform uimage2D ImageLength;

struct ListNode
{
  uint packedColor;
  uint depth;
  uint next;
};

layout(binding = 3, std430) readonly restrict buffer FragmentsList
{
  ListNode fragments[];
};

struct DataNode
{
  uint packedColor;
  uint depth;
};

const int MAX_FRAGMENTS = 16;

void main()
{
  ivec2 p = ivec2(gl_FragCoord.xy);
  uint index = imageLoad(ImageHead, p).r;
  if (index == 0xffffffffu) discard;

  uint len = min(imageLoad(ImageLength, p).r, MAX_FRAGMENTS);

  // Extract linked list
  DataNode sorted[MAX_FRAGMENTS];
  for (int i = 0; i < len; ++i)
  {
    sorted[i].packedColor = fragments[index].packedColor;
    sorted[i].depth = fragments[index].depth;
    index = fragments[index].next;
  }

  // Insertion Sort
  for (int i = 1; i < len; ++i)
  {
    DataNode temp = sorted[i];
    int j = i;
    while (sorted[j - 1].depth < temp.depth)
    {
      sorted[j] = sorted[j - 1];
      --j;
      if (j == 0)
      { break; }
    }
    if (j != i)
    { sorted[j] = temp; }
  }

  vec3 rgb = vec3(0.0);
  float alpha = 1.0;

  for (int i = 0; i < len; ++i)
  {
    vec4 color = unpackUnorm4x8(sorted[i].packedColor);
    alpha *= (1.0 - color.a);
    rgb = mix(rgb, color.rgb, color.a);
  }

  FragColor = vec4(rgb, alpha);
}
