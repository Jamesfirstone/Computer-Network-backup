#include "reassembler.hh"
#include <algorithm>
#include <iostream>

using namespace std;

void Reassembler::insert( uint64_t first_index, string data, bool is_last_substring )
{
  // Your code here.
  // (void)first_index;
  // (void)data;
  // (void)is_last_substring;
  // 如果收到最后一个子字符串，记录相关信息
  if (is_last_substring) {
    has_last_ = true;
    last_index_ = first_index + data.size(); //- 1;
  }

  // 获取当前状态
  const uint64_t first_unassembled = output_.writer().bytes_pushed();
  const uint64_t first_unacceptable = first_unassembled + output_.writer().available_capacity();

  // 处理数据中的每个字节
  for (size_t i = 0; i < data.size(); ++i) {
    const uint64_t current_index = first_index + i;
    
    // 跳过已经组装或超出容量的字节
    if (current_index < first_unassembled) {
      continue; // 字节已经组装
    }
    if (current_index >= first_unacceptable) {
      continue; // 字节超出容量
    }

    // 只存储尚未存在的字节（避免重复存储）
    if (unassembled_bytes_.find(current_index) == unassembled_bytes_.end()) {
      unassembled_bytes_[current_index] = data[i];
    }
  }

  // 尝试推送连续的字节
  push_contiguous_bytes();

  // 检查是否应该关闭流
  check_if_finished();
}

uint64_t Reassembler::bytes_pending() const
{
  // Your code here.
  return unassembled_bytes_.size();
}

void Reassembler::push_contiguous_bytes()
{
  const uint64_t next_expected = output_.writer().bytes_pushed();
  string contiguous_data;
  
  // 收集连续的字节
  auto it = unassembled_bytes_.begin();
  while (it != unassembled_bytes_.end() && it->first == next_expected + contiguous_data.size()) {
    contiguous_data += it->second;
    ++it;
  }

  // 如果有连续的字节，推送到输出流
  if (!contiguous_data.empty()) {
    output_.writer().push(contiguous_data);
    
    // 删除已推送的字节
    for (uint64_t i = 0; i < contiguous_data.size(); ++i) {
      unassembled_bytes_.erase(next_expected + i);
    }
  }
}

void Reassembler::check_if_finished()
{
  // 如果收到了结束标志，并且所有字节都已组装（包括空数据的情况）
  if (has_last_ && output_.writer().bytes_pushed() >= last_index_) {
    output_.writer().close();
  }
}