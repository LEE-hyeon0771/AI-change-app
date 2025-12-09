import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'api_config.dart';

class AdministerPage extends StatefulWidget {
  const AdministerPage({super.key});

  @override
  State<AdministerPage> createState() => _AdministerPageState();
}

class _AdministerPageState extends State<AdministerPage> {
  final _formKey = GlobalKey<FormState>();
  // 제안정보
  final TextEditingController _titleController = TextEditingController(); // 제안명
  final TextEditingController _organizationController =
      TextEditingController(); // 기관명
  final TextEditingController _projectNameController =
      TextEditingController(); // 사업명
  final TextEditingController _clientController =
      TextEditingController(); // 요청 발주처
  final TextEditingController _keywordController =
      TextEditingController(); // 키워드 (선택)
  final TextEditingController _authorController =
      TextEditingController(); // 작성자 (선택)

  // LCC 절감효과
  final TextEditingController _beforeConstCostController =
      TextEditingController();
  final TextEditingController _beforeMaintCostController =
      TextEditingController();
  final TextEditingController _beforeTotalCostController =
      TextEditingController();
  final TextEditingController _afterConstCostController =
      TextEditingController();
  final TextEditingController _afterMaintCostController =
      TextEditingController();
  final TextEditingController _afterTotalCostController =
      TextEditingController();
  final TextEditingController _savingAmountController =
      TextEditingController();
  final TextEditingController _savingRateController = TextEditingController();

  // 가치향상 효과
  final TextEditingController _beforePerfScoreController =
      TextEditingController();
  final TextEditingController _beforeValueScoreController =
      TextEditingController();
  final TextEditingController _afterPerfScoreController =
      TextEditingController();
  final TextEditingController _afterValueScoreController =
      TextEditingController();

  DateTime _selectedDate = DateTime.now();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _titleController.dispose();
    _organizationController.dispose();
    _projectNameController.dispose();
    _clientController.dispose();
    _keywordController.dispose();
    _authorController.dispose();
    _beforeConstCostController.dispose();
    _beforeMaintCostController.dispose();
    _beforeTotalCostController.dispose();
    _afterConstCostController.dispose();
    _afterMaintCostController.dispose();
    _afterTotalCostController.dispose();
    _savingAmountController.dispose();
    _savingRateController.dispose();
    _beforePerfScoreController.dispose();
    _beforeValueScoreController.dispose();
    _afterPerfScoreController.dispose();
    _afterValueScoreController.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked != null) {
      setState(() {
        _selectedDate = picked;
      });
    }
  }

  Future<void> _submitChange() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isSubmitting = true;
    });

    String _trim(String text) => text.trim();

    // 백엔드 description 으로 보낼 통합 설명 텍스트
    final descriptionBuffer = StringBuffer()
      ..writeln('[VE 제안명] ${_trim(_titleController.text)}')
      ..writeln('기관명: ${_trim(_organizationController.text)}')
      ..writeln('사업명: ${_trim(_projectNameController.text)}')
      ..writeln('요청 발주처: ${_trim(_clientController.text)}')
      ..writeln('키워드: ${_trim(_keywordController.text)}')
      ..writeln()
      ..writeln('[생애주기비용(LCC) 절감효과 - 개선전]')
      ..writeln('건설사업 비용(백만원): ${_trim(_beforeConstCostController.text)}')
      ..writeln('유지관리 비용(백만원): ${_trim(_beforeMaintCostController.text)}')
      ..writeln('계(백만원): ${_trim(_beforeTotalCostController.text)}')
      ..writeln()
      ..writeln('[생애주기비용(LCC) 절감효과 - 개선후]')
      ..writeln('건설사업 비용(백만원): ${_trim(_afterConstCostController.text)}')
      ..writeln('유지관리 비용(백만원): ${_trim(_afterMaintCostController.text)}')
      ..writeln('계(백만원): ${_trim(_afterTotalCostController.text)}')
      ..writeln()
      ..writeln('절감액(백만원): ${_trim(_savingAmountController.text)}')
      ..writeln('절감율(%): ${_trim(_savingRateController.text)}')
      ..writeln()
      ..writeln('[가치향상효과 - 개선전]')
      ..writeln('성능점수(점): ${_trim(_beforePerfScoreController.text)}')
      ..writeln('가치점수(점): ${_trim(_beforeValueScoreController.text)}')
      ..writeln()
      ..writeln('[가치향상효과 - 개선후]')
      ..writeln('성능점수(점): ${_trim(_afterPerfScoreController.text)}')
      ..writeln('가치점수(점): ${_trim(_afterValueScoreController.text)}');

    final payload = {
      "change_date": _selectedDate.toIso8601String().split('T').first,
      "title": _trim(_titleController.text),
      "description": descriptionBuffer.toString(),
      "author": _trim(_authorController.text).isEmpty
          ? null
          : _trim(_authorController.text),
      "organization": _trim(_organizationController.text).isEmpty
          ? null
          : _trim(_organizationController.text),
      "project_name": _trim(_projectNameController.text).isEmpty
          ? null
          : _trim(_projectNameController.text),
      "client": _trim(_clientController.text).isEmpty
          ? null
          : _trim(_clientController.text),
    };

    try {
      final uri = Uri.parse('$apiBaseUrl/admin/changes');
      final resp = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );

      if (!mounted) return;

      if (resp.statusCode == 200) {
        _titleController.clear();
        _organizationController.clear();
        _projectNameController.clear();
        _clientController.clear();
        _keywordController.clear();
        _authorController.clear();
        _beforeConstCostController.clear();
        _beforeMaintCostController.clear();
        _beforeTotalCostController.clear();
        _afterConstCostController.clear();
        _afterMaintCostController.clear();
        _afterTotalCostController.clear();
        _savingAmountController.clear();
        _savingRateController.clear();
        _beforePerfScoreController.clear();
        _beforeValueScoreController.clear();
        _afterPerfScoreController.clear();
        _afterValueScoreController.clear();

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('설계 변경이 성공적으로 등록되었습니다.')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                '등록 실패 (${resp.statusCode}): ${resp.body.isNotEmpty ? resp.body : '알 수 없는 오류'}'),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('요청 중 오류가 발생했습니다: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('관리자 페이지'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '변경일: ${_selectedDate.toLocal().toString().split(' ').first}',
                        style: const TextStyle(fontSize: 16),
                      ),
                    ),
                    TextButton.icon(
                      onPressed: _pickDate,
                      icon: const Icon(Icons.calendar_today),
                      label: const Text('날짜 선택'),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
              const Text(
                '제안정보',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
                TextFormField(
                  controller: _titleController,
                  decoration: const InputDecoration(
                  labelText: '제안명',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) {
                    return '제안명을 입력해 주세요.';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                controller: _organizationController,
                  decoration: const InputDecoration(
                  labelText: '기관명',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) {
                    return '기관명을 입력해 주세요.';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
              TextFormField(
                controller: _projectNameController,
                decoration: const InputDecoration(
                  labelText: '사업명',
                  border: OutlineInputBorder(),
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) {
                    return '사업명을 입력해 주세요.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _clientController,
                decoration: const InputDecoration(
                  labelText: '요청 발주처',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _keywordController,
                decoration: const InputDecoration(
                  labelText: '키워드 (선택)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 8),
              const Text(
                '생애주기비용(LCC) 절감효과',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text('개선전'),
              const SizedBox(height: 4),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _beforeConstCostController,
                      decoration: const InputDecoration(
                        labelText: '건설사업 비용(백만원)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextFormField(
                      controller: _beforeMaintCostController,
                      decoration: const InputDecoration(
                        labelText: '유지관리 비용(백만원)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _beforeTotalCostController,
                decoration: const InputDecoration(
                  labelText: '계(백만원)',
                  border: OutlineInputBorder(),
                ),
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
              ),
              const SizedBox(height: 16),
              const Text('개선후'),
              const SizedBox(height: 4),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _afterConstCostController,
                      decoration: const InputDecoration(
                        labelText: '건설사업 비용(백만원)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextFormField(
                      controller: _afterMaintCostController,
                      decoration: const InputDecoration(
                        labelText: '유지관리 비용(백만원)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _afterTotalCostController,
                decoration: const InputDecoration(
                  labelText: '계(백만원)',
                  border: OutlineInputBorder(),
                ),
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _savingAmountController,
                      decoration: const InputDecoration(
                        labelText: '절감액(백만원)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextFormField(
                      controller: _savingRateController,
                      decoration: const InputDecoration(
                        labelText: '절감율(%)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 8),
              const Text(
                '가치향상효과',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text('개선전'),
              const SizedBox(height: 4),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _beforePerfScoreController,
                      decoration: const InputDecoration(
                        labelText: '성능점수(점)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextFormField(
                      controller: _beforeValueScoreController,
                      decoration: const InputDecoration(
                        labelText: '가치점수(점)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Text('개선후'),
              const SizedBox(height: 4),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _afterPerfScoreController,
                      decoration: const InputDecoration(
                        labelText: '성능점수(점)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextFormField(
                      controller: _afterValueScoreController,
                      decoration: const InputDecoration(
                        labelText: '가치점수(점)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
                TextFormField(
                  controller: _authorController,
                  decoration: const InputDecoration(
                    labelText: '작성자 (선택)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _isSubmitting ? null : _submitChange,
                    icon: _isSubmitting
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send),
                    label: Text(_isSubmitting ? '등록 중...' : '설계 변경 등록'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}


