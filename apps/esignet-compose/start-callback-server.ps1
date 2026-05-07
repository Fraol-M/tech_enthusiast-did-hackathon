param(
    [int]$Port = 5555
)

$ErrorActionPreference = "Stop"
$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()

Write-Host "Listening on http://localhost:$Port/"
Write-Host "Open the eSignet authorize URL and leave this window running."
Write-Host "Press Ctrl+C to stop."

try {
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $query = [ordered]@{}

        foreach ($key in $request.QueryString.AllKeys) {
            if ($null -ne $key) {
                $query[$key] = $request.QueryString[$key]
            }
        }

        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-Host ""
        Write-Host "[$timestamp] $($request.HttpMethod) $($request.RawUrl)"
        if ($query.Count -gt 0) {
            $query | ConvertTo-Json -Depth 10 | Write-Host
        }

        $html = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>eSignet Callback</title>
  <style>
    body { font-family: Segoe UI, sans-serif; margin: 2rem; background: #f6f8fa; color: #111827; }
    main { max-width: 900px; margin: 0 auto; background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); }
    pre { background: #0f172a; color: #e2e8f0; padding: 1rem; border-radius: 8px; overflow: auto; }
  </style>
</head>
<body>
  <main>
    <h1>eSignet Callback Received</h1>
    <p>The browser reached the local callback. Query parameters:</p>
    <pre>$([System.Net.WebUtility]::HtmlEncode(($query | ConvertTo-Json -Depth 10)))</pre>
  </main>
</body>
</html>
"@

        $bytes = [System.Text.Encoding]::UTF8.GetBytes($html)
        $context.Response.StatusCode = 200
        $context.Response.ContentType = "text/html; charset=utf-8"
        $context.Response.ContentLength64 = $bytes.Length
        $context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
        $context.Response.OutputStream.Close()
    }
    
} finally {
    $listener.Stop()
    $listener.Close()
}
