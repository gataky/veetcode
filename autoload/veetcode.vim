let s:current_dir = expand("<sfile>:p:h")

python3 <<PYTHON_EOF
import os
import vim

plugin_dir = vim.eval('s:current_dir')

if plugin_dir not in sys.path:
  sys.path.append(plugin_dir)

import leetcode

leetcode.set_cwd(plugin_dir)
PYTHON_EOF



function! veetcode#SetupProblemListBuffer() abort
    setlocal buftype=nofile
    setlocal foldmethod=indent
    setlocal noswapfile
    setlocal nobackup
    setlocal nonumber
    setlocal norelativenumber
    setlocal nospell
    setlocal bufhidden=hide
    setlocal nowrap
    nnoremap <silent> <buffer> <return> :call <SID>HandleCR()<cr>

    call s:SetupHighlighting()
    call s:DisplayFilters()
    call s:DisplayProblems("initial")
endfunction

function! s:DisplayFilters() abort
    let filters = py3eval('leetcode.setup_filters()')
    call append('.', filters)
endfunction

function! s:DisplayProblems(state) abort
    let problems = py3eval('leetcode.setup_problems()')
    if a:state ==# "initial"
        call append('$', problems)
    else
        call search('^Problems$')
        let pos = getpos('.')
        call deletebufline('$', pos[1], '$')
        call append('.', problems)
    endif
endfunction

function! s:SetupHighlighting() abort
    syn match lcEasy   /│ Easy /hs=s+2
    syn match lcMedium /│ Medium /hs=s+2
    syn match lcHard   /│ Hard /hs=s+2

    syn match lcTodo       /│\s*-\s*│/hs=s+1,he=e-1
    syn match lcIncomplete /│\s*☓\s*│/hs=s+1,he=e-1
    syn match lcDone       /│\s*✓\s*│/hs=s+1,he=e-1

    syn match lcFilter /\s\++\S*/hs=s,he=e

    syn match lcPaidOnly /\[P\]/

    hi! lcEasy   ctermfg=lightgreen guifg=lightgreen
    hi! lcMedium ctermfg=yellow     guifg=yellow
    hi! lcHard   ctermfg=red        guifg=red

    hi! lcDone       ctermfg=lightblue guifg=lightblue
    hi! lcTodo       ctermfg=white     guifg=white
    hi! lcIncomplete ctermfg=red       guifg=red

    hi! lcFilter ctermfg=lightgreen guifg=lightgreen

    hi! lcPaid ctermfg=yellow guifg=yellow
endfunction


function! s:HandleCR() abort
    let section = s:GetSection()
    if section ==? 'filters'
        call s:HandleFilters(section)
    elseif section ==? 'problems'
        call s:HandleProblems()
    endif
endfunction


function! s:GetSection() abort
    let pos = getpos('.')
    execute 'normal! {+'
    let section = expand('<cWORD>')
    call setpos('.', pos)

    " if the word we're on is the section then don't do anything
    let word = expand('<cword>')
    if word ==# section
        return ''
    endif

    return section
endfunction


function! s:HandleFilters(section) abort
    let pos = getpos('.')
    let tag = trim(expand('<cWORD>'))
    " if we're on whitespace don't do anything
    if tag ==# ''
        return
    " if the tag is not really a tag but a filter section then return
    elseif tag ==# a:section
        return
    else
        call s:UpdateFilters(tag)
        call s:DisplayProblems("refresh")
    endif
    call setpos('.', pos)
endfunction


function! s:UpdateFilters(tag) abort

    let pos = getpos('.')

    " Search for the start of the section and grab the word
    call search('^\s\{4}\S\+', 'be')
    let section = expand('<cword>')
    let filter_position = getpos('.')
    let upper_line = filter_position[1] + 1

    " Search for the end of the section
    call search('\(^\s\{4}\S\+\|^\n\)')
    let lower_line = getpos('.')[1] - 1

    call deletebufline('$', upper_line, lower_line)

    " Move the pos to the section title so we can append to it.
    call setpos('.', filter_position)

    " construct the python command to get the tags and append to the buffer
    let command = 'leetcode.get_tags("'.section.'", "'.a:tag.'")'
    let tags = py3eval(command)
    call append(filter_position[1], tags)

    call setpos('.', pos)

endfunction

function! s:HandleProblems() abort
    let row_type = s:GetRowType()
    if row_type ==? 'header'
        call s:HandleHeader()
    elseif row_type ==? 'problem'
        call s:HandleProblem()
    endif
endfunction


" GetRowType will check which type of row we're interacting with (header or
" problem) based on the upper left char type of that row.
function! s:GetRowType() abort
    let pos = getpos('.')
    execute 'normal! 0kvy'
    let char = getreg('"')
    call setpos('.', pos)

    if char ==# '╒'
        return 'header'
    else
        return 'problem'
    endif
endfunction

" HandleHeader handles the header row of the problems table.  When a column
" header is selected, the sorting order will change for that column.
function! s:HandleHeader() abort
    " Store the cursor position so we can reset it at the end to avoid the
    " cursor jumping around on us.
    let pos = getpos('.')

    " Select the text between the "|" char.  This is the section we want to
    " toggle the order for.
    execute "normal! T│vt│y"

    " Remove the whitespace from the string
    let header = trim(getreg('"'))

    " Grab the first char from the string.
    let header = header[byteidx(header,1):]
    call py3eval('leetcode.toggle_order("'.header.'")')
    call s:DisplayProblems("refresh")

    call setpos('.', pos)
endfunction


function! s:HandleProblem() abort
    echom "Opening the problem"
endfunction

