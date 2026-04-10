# Function to commit files individually
$files = Get-ChildItem -File -Recurse | Where-Object {$_.FullName -notmatch '\.git'} | Sort-Object FullName

foreach ($file in $files) {
    $relativePath = $file.FullName -replace [regex]::Escape($PWD), ""
    $relativePath = $relativePath.TrimStart('\')
    git add "$relativePath"
    git commit -m "Add: $relativePath" 2>&1 | Select-Object -First 1
}
