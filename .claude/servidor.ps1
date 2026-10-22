# Local static preview of the site (no /api functions: the page falls back to its built-in catalogue).
$root = Split-Path $PSScriptRoot -Parent
$l = [System.Net.HttpListener]::new()
$l.Prefixes.Add('http://localhost:8123/')
$l.Start()
$tipos = @{ '.html' = 'text/html; charset=utf-8'; '.webp' = 'image/webp'; '.png' = 'image/png'; '.js' = 'text/javascript'; '.css' = 'text/css' }
while ($l.IsListening) {
  $c = $l.GetContext()
  $ruta = [Uri]::UnescapeDataString($c.Request.Url.AbsolutePath.TrimStart('/'))
  if ($ruta -eq '') { $ruta = 'index.html' }
  $archivo = Join-Path $root $ruta
  if ((Test-Path $archivo -PathType Leaf) -and -not $ruta.StartsWith('api')) {
    $bytes = [IO.File]::ReadAllBytes($archivo)
    $c.Response.ContentType = $tipos[[IO.Path]::GetExtension($archivo)]
    $c.Response.OutputStream.Write($bytes, 0, $bytes.Length)
  } else {
    $c.Response.StatusCode = 404
  }
  $c.Response.Close()
}
