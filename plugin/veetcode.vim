" vim: sts=4 sw=4 expandtab

if !exists('g:veetcode_problem_directory')
    let g:veetcode_problem_directory = '~/.local/share/veetcode'
endif

command! -nargs=0 VeetCodeList call veetcode#SetupProblemListBuffer()

