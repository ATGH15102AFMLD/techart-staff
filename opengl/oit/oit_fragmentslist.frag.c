#version 430 core

#extension GL_ARB_shader_storage_buffer_object : require
#extension GL_ARB_shader_atomic_counters       : require
#extension GL_ARB_shading_language_packing     : require

layout(early_fragment_tests) in;

out vec4 FragColor;
in float Depth;

uniform vec4 Color;
uniform uint OffsetMax = 0;

layout (binding = 0, offset = 0) uniform atomic_uint Counter;
layout (binding = 1, r32ui) coherent restrict uniform uimage2D ImageHead;
layout (binding = 2, r32ui) coherent restrict uniform uimage2D ImageLength;

struct ListNode
{
  uint packedColor;
  uint depth;
  uint next;
};

layout(binding = 3, std430) writeonly restrict buffer FragmentsList
{
  ListNode fragments[];
};

void main()
{
  FragColor = vec4(0.0);

  uint newOffset = atomicCounterIncrement(Counter);
  if (newOffset >= OffsetMax) discard;

  ivec2 p = ivec2(gl_FragCoord.xy);

  // Write new offset to Head
  uint nextOffset = imageAtomicExchange(ImageHead, p, newOffset);
  // Increment Length
  imageAtomicAdd(ImageLength, p, 1u);

  fragments[newOffset].packedColor = packUnorm4x8(Color);
  fragments[newOffset].depth = floatBitsToUint(Depth);
  fragments[newOffset].next = nextOffset;
}
