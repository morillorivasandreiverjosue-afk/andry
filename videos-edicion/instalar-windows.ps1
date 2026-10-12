# Instalador de herramientas de edición de video para Windows
# Uso: clic derecho en el menú Inicio > "Terminal (Administrador)" y ejecuta:
#   powershell -ExecutionPolicy Bypass -File .\instalar-windows.ps1

$programas = @(
    @{ id = "Gyan.FFmpeg";          nombre = "FFmpeg (motor de video por línea de comandos)" },
    @{ id = "Meltytech.Shotcut";    nombre = "Shotcut (editor de video fácil)" },
    @{ id = "KDE.Kdenlive";         nombre = "Kdenlive (editor de video avanzado)" },
    @{ id = "OBSProject.OBSStudio"; nombre = "OBS Studio (grabar pantalla y cámara)" },
    @{ id = "Audacity.Audacity";    nombre = "Audacity (editar audio y voz)" },
    @{ id = "HandBrake.HandBrake";  nombre = "HandBrake (comprimir y convertir videos)" },
    @{ id = "VideoLAN.VLC";         nombre = "VLC (reproductor que abre todo)" },
    @{ id = "GIMP.GIMP.3";          nombre = "GIMP (editar imágenes y miniaturas)" },
    @{ id = "Python.Python.3.12";   nombre = "Python (para las herramientas de esta carpeta)" }
)

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "No se encontró winget. Instala 'App Installer' desde la Microsoft Store y vuelve a intentarlo." -ForegroundColor Red
    exit 1
}

foreach ($p in $programas) {
    Write-Host "`n==> Instalando $($p.nombre)..." -ForegroundColor Cyan
    winget install --id $p.id -e --accept-source-agreements --accept-package-agreements
}

Write-Host "`n==> Instalando librerías de Python..." -ForegroundColor Cyan
py -m pip install -r "$PSScriptRoot\requirements.txt"

Write-Host "`nListo. Cierra y vuelve a abrir la terminal para que 'ffmpeg' funcione." -ForegroundColor Green
Write-Host "Opcional: DaVinci Resolve (editor profesional gratis) se descarga en https://www.blackmagicdesign.com/products/davinciresolve"
