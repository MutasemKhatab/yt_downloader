import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';

void main() {
  runApp(const MyApp());
}

const backendHttpUrl = 'http://0.0.0.0:5000';
const backendWsUrl = 'ws://192.168.0.129:5000';

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'YT Downloader',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _urlController = TextEditingController(
      text: 'https://www.youtube.com/watch?v=Rd7yyutb-DI');

  bool _loadingInfo = false;
  bool _downloading = false;

  Map<String, dynamic>? _videoInfo;
  List<dynamic> _formats = [];

  String? _selectedFormatId;

  WebSocketChannel? _channel;
  String _progressText = '';

  Future<void> _fetchVideoInfo() async {
    final url = _urlController.text.trim();
    if (url.isEmpty) return;

    setState(() {
      _loadingInfo = true;
      _videoInfo = null;
      _formats = [];
      _selectedFormatId = null;
      _progressText = '';
    });

    try {
      final res = await http.post(
        Uri.parse('$backendHttpUrl/info'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'url': url}),
      );

      if (res.statusCode == 200) {
        final json = jsonDecode(res.body);
        final formats = (json['formats'] as List<dynamic>);
        formats.sort((a, b) {
          // Sort descending by resolution width, then filesize (smaller first)
          int aRes = _parseResolution(a['resolution']);
          int bRes = _parseResolution(b['resolution']);
          if (aRes != bRes) return bRes.compareTo(aRes);
          return (a['filesize'] ?? 0).compareTo(b['filesize'] ?? 0);
        });

        setState(() {
          _videoInfo = json;
          _formats = formats;
          if (formats.isNotEmpty)
            _selectedFormatId = formats.first['format_id'];
        });
      } else {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Failed to load video info')));
      }
    } catch (e) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      setState(() => _loadingInfo = false);
    }
  }

  int _parseResolution(String? res) {
    if (res == null) return 0;
    final parts = res.split('x');
    if (parts.length == 2) {
      return int.tryParse(parts[1]) ?? 0; // Use height as proxy
    }
    if (res.endsWith('p')) {
      return int.tryParse(res.replaceAll('p', '')) ?? 0;
    }
    return 0;
  }

  void _startDownload() {
    if (_selectedFormatId == null || _videoInfo == null) return;

    setState(() {
      _downloading = true;
      _progressText = 'Starting download...';
    });

    // Create a proper Socket.IO WebSocket URL
    final wsUri = Uri.parse(backendWsUrl);
    final socketIoUri = Uri(
        scheme: 'ws',
        host: wsUri.host,
        port: wsUri.port,
        path: '/socket.io/',
        queryParameters: {'EIO': '4', 'transport': 'websocket'});

    try {
      _channel = WebSocketChannel.connect(socketIoUri);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('WebSocket connection error: $e')));
      setState(() {
        _downloading = false;
        _progressText = 'Connection failed';
      });
      return;
    }

    // SocketIO requires a specific connection sequence
    _channel!.sink.add('40'); // Connect to default namespace

    // Wait a moment to ensure connection is established before sending data
    Future.delayed(Duration(milliseconds: 500), () {
      if (_channel != null) {
        _channel!.sink.add(
            '42["start_download",{"url":"${_urlController.text.trim()}","format_id":"$_selectedFormatId"}]');
      }
    });

    _channel!.stream.listen((message) {
      // SocketIO sends messages in a specific format like: 42["event",{data}]
      // We need to parse this properly
      if (message.startsWith('42')) {
        // Extract the JSON part from the message
        final jsonStr = message.substring(2);
        final parsed = jsonDecode(jsonStr);
        final eventName = parsed[0];
        final data = parsed[1];

        if (eventName == 'done' &&
            data.containsKey('status') &&
            data['status'] == 'complete') {
          setState(() {
            _progressText = 'Download complete!';
            _downloading = false;
          });
          _channel!.sink.close();
        } else if (eventName == 'error' && data.containsKey('message')) {
          // Error message from backend
          setState(() {
            _progressText = 'Error: ${data['message']}';
            _downloading = false;
          });
          _channel!.sink.close();
        } else if (eventName == 'progress') {
          // Progress data - display percent and speed if available
          String speed = '';
          if (data['speed'] != null) {
            speed = 'Speed: ${_formatSpeed(data['speed'])}';
          }

          String eta = '';
          if (data['eta'] != null) {
            eta = 'ETA: ${_formatDuration(data['eta'])}';
          }

          final percent = data['percent'] != null
              ? '${data['percent'].toStringAsFixed(1)}%'
              : '';
          final status = data['status'] ?? '';

          setState(() {
            _progressText = 'Status: $status\n$percent $speed $eta';
          });
        }
      }
    }, onDone: () {
      if (mounted) setState(() => _downloading = false);
    }, onError: (error) {
      setState(() {
        _progressText = 'Connection error: $error';
        _downloading = false;
      });
    });
  }

  String _formatSpeed(dynamic speed) {
    if (speed is num) {
      if (speed > 1e6) return '${(speed / 1e6).toStringAsFixed(2)} MB/s';
      if (speed > 1e3) return '${(speed / 1e3).toStringAsFixed(2)} KB/s';
      return '${speed.toStringAsFixed(2)} B/s';
    }
    return '';
  }

  String _formatDuration(dynamic seconds) {
    if (seconds is num) {
      final dur = Duration(seconds: seconds.toInt());
      String twoDigits(int n) => n.toString().padLeft(2, '0');
      final h = twoDigits(dur.inHours);
      final m = twoDigits(dur.inMinutes.remainder(60));
      final s = twoDigits(dur.inSeconds.remainder(60));
      return h == '00' ? '$m:$s' : '$h:$m:$s';
    }
    return '';
  }

  // Helper method removed as we're using inline ScaffoldMessenger calls

  @override
  void dispose() {
    _channel?.sink.close();
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final title = _videoInfo?['title'] ?? 'Paste a YouTube URL and fetch info';
    final uploader = _videoInfo?['uploader'] ?? '';
    final thumbnail = _videoInfo?['thumbnail'];

    return Scaffold(
      appBar: AppBar(title: const Text('YouTube Downloader')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _urlController,
              decoration: const InputDecoration(
                labelText: 'YouTube URL',
                border: OutlineInputBorder(),
              ),
              enabled: !_downloading && !_loadingInfo,
              onSubmitted: (_) => _fetchVideoInfo(),
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed:
                  (_loadingInfo || _downloading) ? null : _fetchVideoInfo,
              child: _loadingInfo
                  ? const SpinKitCircle(color: Colors.white, size: 24)
                  : const Text('Fetch Video Info'),
            ),
            if (thumbnail != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Image.network(thumbnail, height: 150),
              ),
            if (_videoInfo != null)
              Text(
                '$title\nby $uploader',
                style: const TextStyle(fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
            if (_formats.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Text('Select Format (video+audio):'),
              Expanded(
                child: ListView.builder(
                  itemCount: _formats.length,
                  itemBuilder: (context, index) {
                    final format = _formats[index];
                    final formatId = format['format_id'];
                    final ext = format['ext'];
                    final res = format['resolution'] ?? 'unknown';
                    final sizeMB = (format['filesize'] != null)
                        ? (format['filesize'] / (1024 * 1024))
                            .toStringAsFixed(1)
                        : 'N/A';

                    return RadioListTile<String>(
                      title: Text('[$formatId] $ext - $res - $sizeMB MB'),
                      value: formatId,
                      groupValue: _selectedFormatId,
                      onChanged: _downloading
                          ? null
                          : (val) {
                              setState(() {
                                _selectedFormatId = val;
                              });
                            },
                    );
                  },
                ),
              ),
              if (_downloading)
                Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: Text(
                    _progressText,
                    style: const TextStyle(fontSize: 16),
                  ),
                ),
              ElevatedButton(
                onPressed: (_downloading || _selectedFormatId == null)
                    ? null
                    : _startDownload,
                child: const Text('Start Download'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
