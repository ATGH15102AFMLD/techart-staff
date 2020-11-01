#version 430 core

layout (location = 0) in  vec4 vert_poslife;

uniform mat4 MVP;

out float Color;

void main()
{
  gl_Position = MVP * vec4(vert_poslife.xyz, 1.0);
  Color = vert_poslife.w;
}
