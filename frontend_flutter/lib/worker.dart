import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'api_config.dart';

class WorkerPage extends StatefulWidget {
  const WorkerPage({super.key});

  @override
  State<WorkerPage> createState() => _WorkerPageState();
}

class _WorkerPageState extends State<WorkerPage> {
  Timer? _pollTimer;
  String? _latestChangeId;
  String? _latestChangeTitle;
  String? _latestChangeDate;
  String? _latestOrganization;
  String? _latestProjectName;
  String? _latestClient;
  String? _lastSeenChangeId;

  @override
  void initState() {
    super.initState();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  void _startPolling() {
    _pollLatestChange();
    _pollTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      _pollLatestChange();
    });
  }

  Future<void> _pollLatestChange() async {
    try {
      final uri = Uri.parse('$apiBaseUrl/worker/latest-change');
      final resp = await http.get(uri);
      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        if (data['has_change'] == true && data['latest'] != null) {
          final latest = data['latest'] as Map<String, dynamic>;
          setState(() {
            _latestChangeId = latest['id'] as String?;
            _latestChangeTitle = latest['title'] as String?;
            _latestChangeDate = latest['change_date'] as String?;
            _latestOrganization = latest['organization'] as String?;
            _latestProjectName = latest['project_name'] as String?;
            _latestClient = latest['client'] as String?;
          });
        }
      }
    } catch (_) {
      // silent fail for polling
    }
  }

  bool get _hasNewChange {
    if (_latestChangeId == null) return false;
    if (_lastSeenChangeId == null) return true;
    return _latestChangeId != _lastSeenChangeId;
  }

  void _markChangeAsSeen() {
    setState(() {
      _lastSeenChangeId = _latestChangeId;
    });
  }

  void _showLatestChangeDetail() {
    if (_latestChangeId == null) return;
    showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('최근 설계변경 상세'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('기관명: ${_latestOrganization ?? '-'}'),
              Text('사업명: ${_latestProjectName ?? '-'}'),
              Text('제안명: ${_latestChangeTitle ?? '-'}'),
              Text('제안일자: ${_latestChangeDate ?? '-'}'),
              Text('요청 발주처: ${_latestClient ?? '-'}'),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('닫기'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('노동자 페이지'),
      ),
      body: Column(
        children: [
          if (_latestChangeId != null)
            Material(
              elevation: 2,
              color:
                  _hasNewChange ? Colors.orange.shade100 : Colors.grey.shade200,
              child: ListTile(
                leading: Icon(
                  _hasNewChange
                      ? Icons.notifications_active
                      : Icons.notifications,
                  color: _hasNewChange ? Colors.orange : Colors.grey,
                ),
                title: Text(
                  _hasNewChange
                      ? '새 설계변경 사항이 있습니다.'
                      : '마지막 설계변경 사항',
                ),
                subtitle: Text(
                  '${_latestChangeDate ?? ''}  ${_latestChangeTitle ?? ''}',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    TextButton(
                      onPressed:
                          _latestChangeId == null ? null : _showLatestChangeDetail,
                      child: const Text('변경사항 보기'),
                    ),
                    TextButton(
                      onPressed:
                          _latestChangeId == null ? null : _markChangeAsSeen,
                      child: Text(_hasNewChange ? '확인' : '읽음'),
                    ),
                  ],
                ),
              ),
            )
          else
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: Text('등록된 설계변경 정보가 아직 없습니다.'),
            ),
          const Divider(height: 1),
          const Expanded(
            child: DefaultTabController(
              length: 5,
              child: Column(
                children: [
                  TabBar(
                    isScrollable: true,
                    tabs: [
                      Tab(text: '한국어'),
                      Tab(text: 'English'),
                      Tab(text: '中文'),
                      Tab(text: 'Tiếng Việt'),
                      Tab(text: 'Українська'),
                    ],
                  ),
                  Expanded(
                    child: TabBarView(
                      children: [
                        WorkerChatTab(languageCode: 'ko'),
                        WorkerChatTab(languageCode: 'en'),
                        WorkerChatTab(languageCode: 'zh'),
                        WorkerChatTab(languageCode: 'vi'),
                        WorkerChatTab(languageCode: 'uk'),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class WorkerChatMessage {
  final String role; // 'user' or 'assistant'
  final String content;

  WorkerChatMessage({required this.role, required this.content});
}

class WorkerChatTab extends StatefulWidget {
  final String languageCode;

  const WorkerChatTab({super.key, required this.languageCode});

  @override
  State<WorkerChatTab> createState() => _WorkerChatTabState();
}

class _WorkerChatTabState extends State<WorkerChatTab> {
  final TextEditingController _inputController = TextEditingController();
  final List<WorkerChatMessage> _messages = [];
  bool _isSending = false;
  Timer? _streamTimer;

  @override
  void dispose() {
    _streamTimer?.cancel();
    _inputController.dispose();
    super.dispose();
  }

  Future<void> _sendMessage() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || _isSending) return;

    setState(() {
      _messages.add(WorkerChatMessage(role: 'user', content: text));
      _isSending = true;
      _inputController.clear();
    });

    final payload = {
      "language": widget.languageCode,
      "question": text,
      "history": _messages
          .map((m) => {"role": m.role, "content": m.content})
          .toList(),
    };

    try {
      final uri = Uri.parse('$apiBaseUrl/worker/chat');
      final resp = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );

      if (!mounted) return;

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final answer = data['answer'] as String? ?? '';

        // 스트리밍 느낌을 주기 위해 답변을 천천히 타이핑되도록 표시
        if (!mounted) return;
        setState(() {
          _messages.add(
            WorkerChatMessage(role: 'assistant', content: ''),
          );
        });
        final int assistantIndex = _messages.length - 1;
        const duration = Duration(milliseconds: 16);
        const int chunkSize = 3; // 한 번에 보여줄 글자 수
        int offset = 0;

        _streamTimer?.cancel();
        _streamTimer = Timer.periodic(duration, (timer) {
          if (!mounted) {
            timer.cancel();
            return;
          }
          if (offset >= answer.length) {
            timer.cancel();
            return;
          }
          final nextOffset =
              (offset + chunkSize).clamp(0, answer.length).toInt();
          final nextText = answer.substring(0, nextOffset);
          setState(() {
            _messages[assistantIndex] =
                WorkerChatMessage(role: 'assistant', content: nextText);
          });
          offset = nextOffset;
        });
      } else {
        setState(() {
          _messages.add(
            WorkerChatMessage(
              role: 'assistant',
              content:
                  '오류가 발생했습니다. (${resp.statusCode}) 다시 시도해 주세요.',
            ),
          );
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _messages.add(
          WorkerChatMessage(
            role: 'assistant',
            content: '요청 중 오류가 발생했습니다: $e',
          ),
        );
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: _messages.length,
            itemBuilder: (context, index) {
              final msg = _messages[index];
              final isUser = msg.role == 'user';
              return Align(
                alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  padding:
                      const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                  decoration: BoxDecoration(
                    color: isUser
                        ? Theme.of(context).colorScheme.primaryContainer
                        : Theme.of(context).colorScheme.surfaceVariant,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(msg.content),
                ),
              );
            },
          ),
        ),
        const Divider(height: 1),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _inputController,
                  decoration: const InputDecoration(
                    hintText: '질문을 입력하세요...',
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (_) => _sendMessage(),
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                onPressed: _isSending ? null : _sendMessage,
                icon: _isSending
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send),
              ),
            ],
          ),
        ),
      ],
    );
  }
}


