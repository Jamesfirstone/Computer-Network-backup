#include "byte_stream.hh"

using namespace std;

ByteStream::ByteStream( uint64_t capacity )
  : capacity_( capacity )
  , error_( false )
  , buffer_()
  , // 在初始化列表中初始化
  bytes_pushed_( 0 )
  , // 在初始化列表中初始化
  bytes_popped_( 0 )
  ,                // 在初始化列表中初始化
  closed_( false ) // 在初始化列表中初始化
{}

bool Writer::is_closed() const
{
  // Your code here.
  return closed_;
}

void Writer::push( string data )
{
  // Your code here.
  // 如果流已关闭或没有可用容量，直接返回
  if ( closed_ || data.empty() ) {
    return;
  }

  // 计算实际可以写入的数据量
  uint64_t available = available_capacity();
  if ( available == 0 ) {
    return;
  }

  uint64_t bytes_to_write = min( available, data.length() );

  // 将数据写入缓冲区
  buffer_.append( data.substr( 0, bytes_to_write ) );
  bytes_pushed_ += bytes_to_write;
}

void Writer::close()
{
  // Your code here.
  closed_ = true;
}

uint64_t Writer::available_capacity() const
{
  // Your code here.
  // 可用容量 = 总容量 - 当前缓冲区大小
  return capacity_ - buffer_.size();
}

uint64_t Writer::bytes_pushed() const
{
  // Your code here.
  return bytes_pushed_;
}

bool Reader::is_finished() const
{
  // Your code here.
  return closed_ && buffer_.empty();
}

uint64_t Reader::bytes_popped() const
{
  // Your code here.
  return bytes_popped_;
}

string_view Reader::peek() const
{
  // Your code here.
  return string_view( buffer_ );
}

void Reader::pop( uint64_t len )
{
  // Your code here.
  // 确保不会弹出超过缓冲区大小的数据
  uint64_t bytes_to_pop = min( len, buffer_.size() );

  // 从缓冲区前面移除数据
  buffer_.erase( 0, bytes_to_pop );
  bytes_popped_ += bytes_to_pop;
}

uint64_t Reader::bytes_buffered() const
{
  // Your code here.
  // 当前缓冲区大小就是已推送但未弹出的字节数
  return buffer_.size();
}
