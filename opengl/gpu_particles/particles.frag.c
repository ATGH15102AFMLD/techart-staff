#version 430 core

in float Color;

out vec4 frag_color;

void main()
{
  const vec4 color1 = vec4(0.0, 0.00, 0.0, 0.0);
  const vec4 color2 = vec4(0.0, 0.50, 1.0, 1.0);
  const vec4 color3 = vec4(0.6, 0.05, 0.0, 1.0);
  
  if (Color < 0.1)
  {
    frag_color = mix(color1, color2, Color*10.0);
  }
  else if (Color > 0.9)
  {
    frag_color = mix(color3, color1, (Color-0.9)*10.0);
  }
  else
  {
    frag_color = mix(color2, color3, Color);
  }

  frag_color.a = 0.0;
}
