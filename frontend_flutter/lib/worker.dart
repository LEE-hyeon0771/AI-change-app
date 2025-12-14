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

class _WorkerLanguage {
  final String code;
  final String tabLabel;
  final String appBarTitle;
  final String newChangeTitle;
  final String lastChangeTitle;
  final String noChangeText;
  final String viewChangeButton;
  final String confirmButtonNew;
  final String confirmButtonRead;
  final String dialogTitle;
  final String fieldOrganization;
  final String fieldProject;
  final String fieldProposal;
  final String fieldDate;
  final String fieldClient;
  final String inputHint;
  final String closeLabel;

  const _WorkerLanguage({
    required this.code,
    required this.tabLabel,
    required this.appBarTitle,
    required this.newChangeTitle,
    required this.lastChangeTitle,
    required this.noChangeText,
    required this.viewChangeButton,
    required this.confirmButtonNew,
    required this.confirmButtonRead,
    required this.dialogTitle,
    required this.fieldOrganization,
    required this.fieldProject,
    required this.fieldProposal,
    required this.fieldDate,
    required this.fieldClient,
    required this.inputHint,
    required this.closeLabel,
  });
}

const List<_WorkerLanguage> _workerLanguages = [
  _WorkerLanguage(
    code: 'ko',
    tabLabel: '한국어',
    appBarTitle: '작업자 페이지',
    newChangeTitle: '새 설계변경 사항이 있습니다.',
    lastChangeTitle: '마지막 설계변경 사항',
    noChangeText: '등록된 설계변경 정보가 아직 없습니다.',
    viewChangeButton: '변경사항 보기',
    confirmButtonNew: '확인',
    confirmButtonRead: '읽음',
    dialogTitle: '최근 설계변경 상세',
    fieldOrganization: '기관명',
    fieldProject: '사업명',
    fieldProposal: '제안명',
    fieldDate: '제안일자',
    fieldClient: '요청 발주처',
    inputHint: '질문을 입력하세요...',
    closeLabel: '닫기',
  ),
  _WorkerLanguage(
    code: 'en',
    tabLabel: 'English',
    appBarTitle: 'Worker Page',
    newChangeTitle: 'New design change is available.',
    lastChangeTitle: 'Last design change',
    noChangeText: 'No design change information has been registered yet.',
    viewChangeButton: 'View details',
    confirmButtonNew: 'Acknowledge',
    confirmButtonRead: 'Read',
    dialogTitle: 'Latest design change details',
    fieldOrganization: 'Organization',
    fieldProject: 'Project',
    fieldProposal: 'Proposal',
    fieldDate: 'Proposal date',
    fieldClient: 'Client / Ordering party',
    inputHint: 'Type your question here...',
    closeLabel: 'Close',
  ),
  _WorkerLanguage(
    code: 'zh',
    tabLabel: '中文',
    appBarTitle: '工人页面',
    newChangeTitle: '有新的设计变更。',
    lastChangeTitle: '最新的设计变更',
    noChangeText: '尚未登记任何设计变更信息。',
    viewChangeButton: '查看变更内容',
    confirmButtonNew: '确认',
    confirmButtonRead: '已读',
    dialogTitle: '最近设计变更详情',
    fieldOrganization: '机构',
    fieldProject: '项目名称',
    fieldProposal: '提案名称',
    fieldDate: '提案日期',
    fieldClient: '发包方',
    inputHint: '请输入您的问题…',
    closeLabel: '关闭',
  ),
  _WorkerLanguage(
    code: 'vi',
    tabLabel: 'Tiếng Việt',
    appBarTitle: 'Trang công nhân',
    newChangeTitle: 'Có thay đổi thiết kế mới.',
    lastChangeTitle: 'Thay đổi thiết kế gần nhất',
    noChangeText: 'Chưa có thông tin thay đổi thiết kế nào được đăng ký.',
    viewChangeButton: 'Xem chi tiết',
    confirmButtonNew: 'Đã xem',
    confirmButtonRead: 'Đã đọc',
    dialogTitle: 'Chi tiết thay đổi thiết kế mới nhất',
    fieldOrganization: 'Cơ quan',
    fieldProject: 'Tên dự án',
    fieldProposal: 'Tên đề xuất',
    fieldDate: 'Ngày đề xuất',
    fieldClient: 'Chủ đầu tư / đơn vị yêu cầu',
    inputHint: 'Nhập câu hỏi của bạn...',
    closeLabel: 'Đóng',
  ),
  _WorkerLanguage(
    code: 'uk',
    tabLabel: 'Українська',
    appBarTitle: 'Сторінка працівника',
    newChangeTitle: 'Зʼявилися нові зміни в проєкті.',
    lastChangeTitle: 'Останні зміни в проєкті',
    noChangeText: 'Інформація про зміни в проєкті ще не зареєстрована.',
    viewChangeButton: 'Переглянути зміни',
    confirmButtonNew: 'Підтвердити',
    confirmButtonRead: 'Прочитано',
    dialogTitle: 'Деталі останньої зміни проєкту',
    fieldOrganization: 'Організація',
    fieldProject: 'Проєкт',
    fieldProposal: 'Назва пропозиції',
    fieldDate: 'Дата пропозиції',
    fieldClient: 'Замовник',
    inputHint: 'Введіть ваше запитання...',
    closeLabel: 'Закрити',
  ),
];

class _WorkerPageState extends State<WorkerPage>
    with SingleTickerProviderStateMixin {
  Timer? _pollTimer;
  String? _latestChangeId;
  String? _latestChangeTitle;
  String? _latestChangeDate;
  String? _latestOrganization;
  String? _latestProjectName;
  String? _latestClient;
  String? _lastSeenChangeId;
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: _workerLanguages.length,
      vsync: this,
    );
    _tabController.addListener(() {
      if (mounted) setState(() {});
    });
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _tabController.dispose();
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

  Future<void> _showLatestChangeDetail() async {
    if (_latestChangeId == null) return;
    final lang = _workerLanguages[_tabController.index];

    Map<String, dynamic>? translated;
    try {
      final uri = Uri.parse(
        '$apiBaseUrl/worker/latest-change-translated?language=${lang.code}',
      );
      final resp = await http.get(uri);
      if (resp.statusCode == 200) {
        translated = jsonDecode(resp.body) as Map<String, dynamic>;
      }
    } catch (_) {
      // 실패 시 아래에서 원문 메타데이터로 폴백
    }

    String org =
        translated != null ? (translated['organization'] as String? ?? '') : '';
    String proj = translated != null
        ? (translated['project_name'] as String? ?? '')
        : '';
    String title =
        translated != null ? (translated['title'] as String? ?? '') : '';
    String date =
        translated != null ? (translated['change_date'] as String? ?? '') : '';
    String client =
        translated != null ? (translated['client'] as String? ?? '') : '';

    if (org.trim().isEmpty) {
      org = _latestOrganization ?? '-';
    }
    if (proj.trim().isEmpty) {
      proj = _latestProjectName ?? '-';
    }
    if (title.trim().isEmpty) {
      title = _latestChangeTitle ?? '-';
    }
    if (date.trim().isEmpty) {
      date = _latestChangeDate ?? '-';
    }
    if (client.trim().isEmpty) {
      client = _latestClient ?? '-';
    }

    final buffer = StringBuffer()
      ..writeln('${lang.fieldOrganization}: $org')
      ..writeln('${lang.fieldProject}: $proj')
      ..writeln('${lang.fieldProposal}: $title')
      ..writeln('${lang.fieldDate}: $date')
      ..writeln('${lang.fieldClient}: $client');
    final contentText = buffer.toString();

    if (!mounted) return;

    showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: Colors.white,
          titleTextStyle: const TextStyle(
            color: Colors.black87,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
          contentTextStyle: const TextStyle(
            color: Colors.black87,
            fontSize: 14,
          ),
          title: Text(lang.dialogTitle),
          content: SingleChildScrollView(
            child: Text(contentText),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text(
                lang.closeLabel,
                style: const TextStyle(color: Colors.black87),
              ),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final base = Theme.of(context);
    final lightTheme = base.copyWith(
      scaffoldBackgroundColor: const Color(0xFFF3F4F6),
      textTheme: ThemeData.light().textTheme,
      appBarTheme: base.appBarTheme.copyWith(
        backgroundColor: Colors.white,
        foregroundColor: Colors.black87,
        titleTextStyle: const TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: Colors.black87,
        ),
      ),
    );
    final cs = lightTheme.colorScheme;

    final currentLang = _workerLanguages[_tabController.index];

    return Theme(
      data: lightTheme,
      child: Scaffold(
        appBar: AppBar(
          title: Text(currentLang.appBarTitle),
        ),
        body: Column(
          children: [
            const SizedBox(height: 8),
            if (_latestChangeId != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Container(
                  decoration: BoxDecoration(
                    color: _hasNewChange
                        ? cs.primary.withOpacity(0.12)
                        : Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: _hasNewChange
                          ? cs.primary.withOpacity(0.4)
                          : const Color(0xFFE5E7EB),
                    ),
                  ),
                  child: ListTile(
                    leading: Icon(
                      _hasNewChange
                          ? Icons.notifications_active
                          : Icons.notifications,
                      color: _hasNewChange ? cs.primary : Colors.grey.shade500,
                    ),
                    title: Text(_hasNewChange
                        ? currentLang.newChangeTitle
                        : currentLang.lastChangeTitle),
                    subtitle: Text(
                      '${_latestChangeDate ?? ''}  ${_latestChangeTitle ?? ''}',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    trailing: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        TextButton(
                          onPressed: _latestChangeId == null
                              ? null
                              : _showLatestChangeDetail,
                          child: Text(currentLang.viewChangeButton),
                        ),
                        TextButton(
                          onPressed: _latestChangeId == null
                              ? null
                              : _markChangeAsSeen,
                          child: Text(_hasNewChange
                              ? currentLang.confirmButtonNew
                              : currentLang.confirmButtonRead),
                        ),
                      ],
                    ),
                  ),
                ),
              )
            else
              const Padding(
                padding: EdgeInsets.all(8.0),
                child: Text(''),
              ),
            const SizedBox(height: 8),
            const Divider(height: 1, color: Color(0xFFE5E7EB)),
            Expanded(
              child: Column(
                children: [
                  TabBar(
                    controller: _tabController,
                    isScrollable: true,
                    tabs: _workerLanguages
                        .map((l) => Tab(text: l.tabLabel))
                        .toList(),
                  ),
                  Expanded(
                    child: TabBarView(
                      controller: _tabController,
                      children: _workerLanguages
                          .map(
                            (l) => WorkerChatTab(
                              languageCode: l.code,
                              uiLanguage: l,
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
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
  final _WorkerLanguage uiLanguage;

  const WorkerChatTab({
    super.key,
    required this.languageCode,
    required this.uiLanguage,
  });

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
    final cs = Theme.of(context).colorScheme;
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
                alignment:
                    isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  padding:
                      const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                  decoration: BoxDecoration(
                    color: isUser
                        ? cs.primary.withOpacity(0.12)
                        : Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.06),
                    ),
                  ),
                  child: Text(msg.content),
                ),
              );
            },
          ),
        ),
        const Divider(height: 1, color: Color(0xFFE5E7EB)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _inputController,
                  style: const TextStyle(color: Colors.black87),
                  decoration: InputDecoration(
                    hintText: widget.uiLanguage.inputHint,
                    hintStyle: const TextStyle(color: Color(0xFF9CA3AF)),
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(16),
                      borderSide: const BorderSide(
                        color: Color(0xFFE5E7EB),
                      ),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(16),
                      borderSide: const BorderSide(
                        color: Color(0xFFE5E7EB),
                      ),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(16),
                      borderSide: BorderSide(
                        color: cs.primary.withOpacity(0.8),
                      ),
                    ),
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
                color: cs.primary,
              ),
            ],
          ),
        ),
      ],
    );
  }
}


