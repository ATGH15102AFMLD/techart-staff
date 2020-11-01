#version 330 core

layout (location = 0) in vec2 vert_pos;
layout (location = 1) in vec2 vert_uv;

out vec2 UV;

void main()
{
  gl_Position = vec4(vert_pos, 0.0, 1.0);
  UV = vert_uv;
}