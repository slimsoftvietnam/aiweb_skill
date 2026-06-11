# Chay sau khi dang nhap GitHub account slimsoftvietnam: gh auth login

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

gh repo create slimsoftvietnam/aiweb_skill --public --description "Agent skills and migration tools for AIPage" 2>$null
git push -u origin main

Write-Host "Done: https://github.com/slimsoftvietnam/aiweb_skill"
