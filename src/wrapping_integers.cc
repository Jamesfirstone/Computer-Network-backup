#include "wrapping_integers.hh"

using namespace std;

Wrap32 Wrap32::wrap( uint64_t n, Wrap32 zero_point )
{
  // Your code here.
  return zero_point + static_cast<uint32_t>(n);
}

uint64_t Wrap32::unwrap( Wrap32 zero_point, uint64_t checkpoint ) const
{
  // Your code here.
  // 将当前序列号转换为绝对序列号，选择最接近checkpoint的值
  const uint64_t base = checkpoint & 0xFFFFFFFF00000000;
  const uint32_t offset = raw_value_ - zero_point.raw_value_;
  
  // 考虑三种可能：base - 2^32, base, base + 2^32
  const uint64_t candidate1 = base - (1ULL << 32) + offset;
  const uint64_t candidate2 = base + offset;
  const uint64_t candidate3 = base + (1ULL << 32) + offset;
  
  // 选择最接近checkpoint的候选值
  const uint64_t diff1 = checkpoint > candidate1 ? checkpoint - candidate1 : candidate1 - checkpoint;
  const uint64_t diff2 = checkpoint > candidate2 ? checkpoint - candidate2 : candidate2 - checkpoint;
  const uint64_t diff3 = candidate3 > checkpoint ? candidate3 - checkpoint : checkpoint - candidate3;
  
  if (diff1 <= diff2 && diff1 <= diff3) return candidate1;
  if (diff2 <= diff3) return candidate2;
  return candidate3;
}
