param([Parameter(Mandatory=$true)][string]$ImagePath)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$storageType = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$streamType = [Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$decoderType = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$bitmapType = [Windows.Graphics.Imaging.SoftwareBitmap,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$ocrType = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$resultType = [Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]
$languageType = [Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1

function Await-Result($Operation, [Type]$Result) {
    $task = $asTask.MakeGenericMethod($Result).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}

$resolvedImage = (Resolve-Path -LiteralPath $ImagePath).Path
$file = Await-Result ($storageType::GetFileFromPathAsync($resolvedImage)) $storageType
$stream = Await-Result ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) $streamType
try {
    $decoder = Await-Result ($decoderType::CreateAsync($stream)) $decoderType
    $bitmap = Await-Result ($decoder.GetSoftwareBitmapAsync()) $bitmapType
    try {
        $engine = $ocrType::TryCreateFromLanguage($languageType::new('ko'))
        if ($null -eq $engine) { throw 'Windows Korean OCR language is not installed.' }
        $result = Await-Result ($engine.RecognizeAsync($bitmap)) $resultType
        $lines = @($result.Lines | Where-Object {
            $top = ($_.Words | ForEach-Object { $_.BoundingRect.Y } | Measure-Object -Minimum).Minimum
            $top -ge $bitmap.PixelHeight * 0.5 -and $top -lt $bitmap.PixelHeight * 0.96
        } | ForEach-Object { $_.Text })
        @{lines=$lines} | ConvertTo-Json -Depth 3 -Compress
    } finally { $bitmap.Dispose() }
} finally { $stream.Dispose() }
