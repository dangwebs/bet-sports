import React from "react";
import { Box } from "@mui/material";
import { useImageColor } from "../../../hooks/useImageColor";

interface TeamLogoProps {
  src: string;
  alt: string;
  size?: number | string;
  width?: any;
  height?: any;
  sx?: any;
}

export const TeamLogo: React.FC<TeamLogoProps> = ({
  src,
  alt,
  size = 48,
  width,
  height,
  sx,
}) => {
  const glowColor = useImageColor(src);

  // Use specific width/height if provided, else define square size
  const finalWidth = width || size;
  const finalHeight = height || size;

  return (
    <Box
      component="img"
      src={src}
      alt={alt}
      crossOrigin="anonymous" // Important for canvas extraction
      sx={{
        width: finalWidth,
        height: finalHeight,
        objectFit: "contain",
        transition: "filter 0.5s ease",
        filter: glowColor
          ? `drop-shadow(0 0 12px ${glowColor}) drop-shadow(0 0 4px ${glowColor})`
          : "none",
        ...sx,
      }}
    />
  );
};
