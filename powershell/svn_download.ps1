# Texture downloader from SVN

$SVN = "https://svn.some.address"
$REGEX = "*.tga"

Write-Host "Collect SVN files from " $SVN -ForegroundColor Blue
Write-Progress -Activity "Please wait" -Status "..."
svn ls $SVN --recursive | Where-Object {($_ -like $REGEX)} | Out-File svn.txt

[decimal] $COUNT = (Get-Content svn.txt | Measure-Object).Count

$QUESTION = "Download $COUNT files ? [y/n]"
$ANSWER = Read-Host $QUESTION
while("y","n" -notcontains $ANSWER) { $ANSWER = Read-Host $QUESTION }
if ($ANSWER -like "n") { exit 1 }

Write-Host "Export files from " $SVN -ForegroundColor Blue

[decimal] $I = 0
foreach($line in Get-Content .\svn.txt) {
    # Write-Host $line
    $outputPath = Split-Path -Path $line
    # $outputFile = Split-Path -Path $line -Leaf        
    # Write-Host $outputPath "&" $outputFile
    
    # Create dir
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
    
    svn export $SVN/$line ./$line --force | Out-Null
    if ($LASTEXITCODE -ne 0) { 
        Write-Host "L"$I.ToString("00000")": $line" 
    }
    
    Write-Progress -Activity "Download textures" -Status 'Progress:' -PercentComplete ($I / $COUNT * 100) -CurrentOperation ("$I/$COUNT $line")
    $I++
}