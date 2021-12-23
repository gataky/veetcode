" vim: sts=4 sw=4 expandtab

if !exists('g:veetcode_problemset')
    let g:veetcode_problemset = 'all'
endif

command! -nargs=0 VeetCodeList call veetcode#SetupProblemListBuffer()

